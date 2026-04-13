"""
Workflow 1: 处理 Starred Items

流程：
1. 获取 FreshRSS Starred items
2. 提取番号和磁力链接
3. 分类处理：
   - 无磁力 → 标签"无磁力链接" → 取消星标
   - 有磁力 → 检查数据库
     - 重复 → 标签"已重复" → 取消星标
     - 新任务 → BitComet下载
       - 成功 → 标签"已开始下载" → 写入数据库 → 取消星标
       - 失败 → 标签"下载错误" → （保留星标或取消，看策略）
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from app.services import FreshRSSClient, BitCometClient
from app.database import get_db_session, DownloadRecord
from app.config import settings
from app.logger import logger, log_workflow_start, log_workflow_end, log_task_started, log_task_error


class DownloadWorkflow:
    """下载工作流"""
    
    # FreshRSS 标签常量
    TAG_STARTED = "已开始下载"
    TAG_COMPLETED = "下载完成"
    TAG_ERROR = "下载错误"
    TAG_NO_MAGNET = "无磁力链接"
    TAG_FETCH_FAILED = "源站抓取失败"
    TAG_DUPLICATE = "已重复"
    
    def __init__(self):
        self.freshrss = FreshRSSClient()
        self.bitcomet = BitCometClient()
        
    async def __aenter__(self):
        await self.freshrss.connect()
        await self.bitcomet.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.freshrss.close()
        await self.bitcomet.close()
    
    async def run(self) -> dict:
        """
        执行完整工作流
        
        处理两类项目：
        1. Starred items（正常流程）
        2. 带有"源站抓取失败"标签的项目（重试流程）
        
        Returns:
            执行统计信息
        """
        stats = {
            "total": 0,
            "no_magnet": 0,      # 无磁力链接
            "duplicate": 0,      # 重复任务
            "started": 0,        # 开始下载
            "failed": 0,         # 下载错误
            "retry_success": 0,  # 重试成功
        }
        
        # 简洁日志：工作流开始
        log_workflow_start("W1-下载任务")
        
        # DEBUG 模式下输出详细信息
        logger.debug(f"获取 Starred items 和重试项目")
        
        # 1. 获取 Starred items
        starred_items = await self.freshrss.get_starred_items()
        
        # 2. 获取带有"源站抓取失败"标签的项目（用于重试）
        retry_items = await self.freshrss.get_items_by_tag(self.TAG_FETCH_FAILED)
        
        # 合并项目列表，去重（以 item_id 为准）
        all_items_map = {}
        for item in starred_items:
            all_items_map[item.item_id] = (item, False)  # (item, is_retry)
        for item in retry_items:
            if item.item_id not in all_items_map:
                all_items_map[item.item_id] = (item, True)  # 标记为重试项目
        
        all_items = list(all_items_map.values())
        stats["total"] = len(all_items)
        
        if not all_items:
            logger.info("无任务")
            return stats
        
        # 简洁日志：显示任务数量
        if len(starred_items) > 0:
            logger.info(f"📥 星标: {len(starred_items)}")
        if len(retry_items) > 0:
            logger.info(f"🔄 重试: {len(retry_items)}")
        
        # 3. 循环处理每个 item
        db = get_db_session()
        try:
            for item, is_retry in all_items:
                if is_retry:
                    await self._process_retry_item(item, db, stats)
                else:
                    await self._process_item(item, db, stats)
        finally:
            db.close()
        
        # 简洁日志：工作流结束
        log_workflow_end("W1-下载任务", stats)
        
        return stats
    
    async def _process_item(self, item, db: Session, stats: dict):
        """处理单个 item"""
        content_id = item.uid
        item_id = item.item_id
        
        logger.debug(f"处理: {item.title[:50]}")
        
        # 步骤 1: 检查是否提取到番号
        if not content_id:
            logger.warning(f"⚠️ 无番号: {item.title[:30]}")
            await self._mark_item(item_id, self.TAG_NO_MAGNET, cancel_star=True)
            stats["no_magnet"] += 1
            return
        
        # 步骤 2: 检查是否有磁力链接
        if not item.magnet_url:
            logger.debug(f"尝试抓取磁力: {content_id}")
            
            fetched_magnet = await item.fetch_magnet_from_source(
                rsshub_base_url=settings.rsshub_base_url
            )
            
            if not fetched_magnet:
                logger.info(f"⏹️ 无磁力: {content_id}")
                if item.source_url:
                    await self._mark_item(item_id, self.TAG_FETCH_FAILED, cancel_star=True)
                else:
                    await self._mark_item(item_id, self.TAG_NO_MAGNET, cancel_star=True)
                stats["no_magnet"] += 1
                return
            
            logger.info(f"🔄 重试成功: {content_id}")
        
        # 步骤 3: 检查数据库重复
        existing = db.query(DownloadRecord).filter(
            DownloadRecord.content_id == content_id
        ).first()
        
        if existing:
            await self._handle_duplicate(item, existing, db, stats)
        else:
            # 新任务，尝试下载
            await self._handle_new_task(item, db, stats)
    
    async def _process_retry_item(self, item, db: Session, stats: dict):
        """
        处理重试项目（带有"源站抓取失败"标签的项目）
        
        逻辑：
        1. 尝试从 RSSHub 抓取磁力链接
        2. 如果抓取成功 → 执行正常下载流程，移除"源站抓取失败"标签，添加"已开始下载"标签
        3. 如果抓取失败 → 保持不动（不打新标签，不取消标签）
        """
        content_id = item.uid
        item_id = item.item_id
        
        logger.debug(f"重试: {item.title[:40]}")
        
        # 步骤 1: 检查是否提取到番号
        if not content_id:
            logger.warning(f"⚠️ 无番号: {item.title[:30]}")
            return
        
        # 步骤 2: 检查数据库是否已存在（可能之前已下载）
        existing = db.query(DownloadRecord).filter(
            DownloadRecord.content_id == content_id
        ).first()
        
        if existing:
            logger.debug(f"已存在: {content_id}")
            await self._remove_tag_only(item_id, self.TAG_FETCH_FAILED)
            return
        
        # 步骤 3: 尝试从 RSSHub 抓取磁力链接
        fetched_magnet = await item.fetch_magnet_from_source(
            rsshub_base_url=settings.rsshub_base_url
        )
        
        if not fetched_magnet:
            logger.debug(f"重试无果: {content_id}")
            return
        
        logger.info(f"🎯 重试成功: {content_id}")
        
        # 步骤 4: 执行正常下载流程
        await self._handle_new_task(item, db, stats, is_retry=True)
    
    async def _remove_tag_only(self, item_id: str, tag: str):
        """
        仅移除标签，不取消星标
        
        用于重试项目发现数据库已存在时清理标签
        """
        try:
            await self.freshrss.remove_tag(item_id, tag)
        except Exception as e:
            logger.debug(f"移除标签失败: {tag} - {e}")
    
    async def _handle_retry_success_tags(self, item_id: str):
        """
        处理重试成功的标签操作
        
        - 移除"源站抓取失败"标签
        - 添加"已开始下载"标签
        """
        try:
            await self.freshrss.remove_tag(item_id, self.TAG_FETCH_FAILED)
            await self.freshrss.add_tag(item_id, self.TAG_STARTED)
        except Exception as e:
            logger.warning(f"标签更新失败: {e}")
    
    async def _handle_new_task(self, item, db: Session, stats: dict, is_retry: bool = False):
        """处理新任务 - 尝试 BitComet 下载"""
        content_id = item.uid
        item_id = item.item_id
        
        try:
            # BitComet 登录
            if not self.bitcomet._device_token:
                await self.bitcomet.login()
            
            # 添加 BitComet 任务
            save_folder = settings.bitcomet_download_path
            task_id = await self.bitcomet.add_task(
                magnet_url=item.magnet_url,
                save_path=save_folder
            )
            
            if not task_id:
                log_task_error(content_id, "BitComet添加失败")
                await self._mark_item(item_id, self.TAG_ERROR, cancel_star=True)
                stats["failed"] += 1
                return
            
            log_task_started(content_id)
            
            # 获取 task_guid
            task_guid = None
            try:
                await asyncio.sleep(1)  # 等待任务创建完成
                task_list = await self.bitcomet.get_task_list()
                for task in task_list:
                    if task.task_id == task_id:
                        task_guid = task.task_guid
                        break
            except Exception as e:
                logger.warning(f"  ⚠️  获取 task_guid 失败: {e}")
            
            # 写入数据库
            record = DownloadRecord(
                content_id=content_id,
                content_title=item.title,
                magnet_url=item.magnet_url,
                freshrss_item_id=item_id,
                id_entry=item.id_entry,
                bitcomet_task_id=str(task_id),
                bitcomet_task_guid=task_guid,
                status="running",
                save_folder=save_folder,
                tags=self.TAG_STARTED,
            )
            db.add(record)
            db.commit()
            logger.debug(f"数据库记录: id={record.id}")
            
            # 关键步骤：处理标签
            if is_retry:
                await self._handle_retry_success_tags(item_id)
                stats["retry_success"] += 1
            else:
                await self._mark_item(item_id, self.TAG_STARTED, cancel_star=True)
            
            stats["started"] += 1
            
        except Exception as e:
            logger.error(f"✗ {content_id}: {str(e)[:50]}")
            await self._mark_item(item_id, self.TAG_ERROR, cancel_star=True)
            stats["failed"] += 1
            db.rollback()
    
    async def _handle_duplicate(self, item, existing: DownloadRecord, db: Session, stats: dict):
        """处理重复任务"""
        content_id = item.uid
        item_id = item.item_id
        
        logger.info(f"🔁 重复: {content_id}")
        
        # 计算时间差
        time_diff = datetime.utcnow() - existing.created_at
        
        if time_diff > timedelta(days=2):
            # 场景 A: 超过 2 天，删除旧任务，重新下载
            logger.info(f"    旧任务超过 2 天，删除并重启: {content_id}")
            
            try:
                # 删除旧 BitComet 任务
                if existing.bitcomet_task_id:
                    await self._delete_bitcomet_task(existing)
                
                # 更新旧记录状态
                existing.status = "duplicate_cancelled"
                existing.tags = f"{self.TAG_ERROR},旧任务已删除重新下载"
                db.commit()
                
                # 走新任务流程
                await self._handle_new_task(item, db, stats)
                
            except Exception as e:
                logger.exception(f"    处理重复任务失败: {e}")
                await self._mark_item(item_id, self.TAG_ERROR, cancel_star=True)
                stats["failed"] += 1
        else:
            # 场景 B: 未超 2 天，标记为重复并跳过
            logger.info(f"    任务未超 2 天，标记为重复: {content_id}")
            await self._mark_item(item_id, self.TAG_DUPLICATE, cancel_star=True)
            stats["duplicate"] += 1
    
    async def _delete_bitcomet_task(self, record: DownloadRecord):
        """删除 BitComet 任务"""
        deleted = False
        
        # 优先使用 task_guid
        if record.bitcomet_task_guid:
            try:
                tasks = await self.bitcomet.get_task_list()
                for task in tasks:
                    if task.task_guid == record.bitcomet_task_guid:
                        await self.bitcomet.delete_task(task.task_id, action="delete_all")
                        deleted = True
                        logger.debug(f"删除旧任务: {task.task_id}")
                        break
            except Exception as e:
                logger.debug(f"删除旧任务失败: {e}")
        
        # 备用：使用 task_id
        if not deleted and record.bitcomet_task_id:
            try:
                await self.bitcomet.delete_task(int(record.bitcomet_task_id), action="delete_all")
                logger.debug(f"删除旧任务: {record.bitcomet_task_id}")
            except Exception as e:
                logger.debug(f"删除旧任务失败: {e}")
    
    async def _mark_item(self, item_id: str, tag: str, cancel_star: bool = True):
        """
        标记 FreshRSS 条目
        
        Args:
            item_id: FreshRSS 条目 ID
            tag: 要添加的标签
            cancel_star: 是否取消星标
        """
        try:
            # 添加标签
            await self.freshrss.add_tag(item_id, tag)
            
            # 取消星标
            if cancel_star:
                await self.freshrss.unstar_item(item_id)
                    
        except Exception as e:
            logger.warning(f"标签失败: {tag} - {e}")
