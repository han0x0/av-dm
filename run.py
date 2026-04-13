#!/usr/bin/env python3
"""
AV Download Manager - 启动脚本

用法:
    python run.py              # 启动调度器（默认）
    python run.py --once       # 执行一次所有工作流
    python run.py --once w1    # 执行一次 Workflow 1
    python run.py --once w1 w2 # 执行一次 Workflow 1 和 2
"""

import asyncio
import sys
import argparse

from app.main import Application
from app.database import init_db
from app.logger import logger


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="AV Download Manager - 自动化下载管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
工作流说明:
    w1  - Workflow 1: 处理 Starred Items (FreshRSS → BitComet)
    w2  - Workflow 2: 状态监控 & JavSP 整理
    w3  - Workflow 3 & 4: 空间管理 & 整理完成检测
        """
    )
    
    parser.add_argument(
        "--once",
        nargs="*",
        metavar="WORKFLOW",
        help="立即执行一次指定工作流 (w1/w2/w3)，不指定则执行全部",
    )
    
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="仅初始化数据库，不启动调度器",
    )
    
    return parser.parse_args()


async def main():
    args = parse_args()
    
    # 仅初始化数据库
    if args.init_db:
        logger.info("初始化数据库...")
        init_db()
        logger.info("数据库初始化完成")
        return
    
    app = Application()
    
    # 执行一次模式
    if args.once is not None:
        # 初始化数据库
        init_db()
        
        # 确定要执行的工作流
        workflows = args.once if args.once else ['w1', 'w2', 'w3']
        await app.run_once(workflows)
        return
    
    # 正常启动调度器
    await app.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"程序异常: {e}")
        sys.exit(1)
