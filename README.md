# AV Download Manager

自动化下载管理项目 - 连接 FreshRSS → BitComet → JavSP-Web → Jellyfin 的全自动下载整理流程。

## 🆕 Web UI 管理界面

本项目现在包含一个现代化的 Web 管理界面，可以方便地查看任务状态、控制工作流、查看日志等。

### Web UI 功能

- **📊 仪表盘**: 实时查看任务统计、磁盘使用、工作流状态
- **📋 任务管理**: 查看、筛选、搜索任务，支持重试/取消/删除操作
- **📝 日志查看**: 实时查看系统日志，支持级别筛选和关键字搜索
- **⚙️ 系统设置**: **实时配置管理**、服务连接测试、配置备份/恢复
- **🌙 深色模式**: 支持浅色/深色主题切换，自动跟随系统偏好，一键切换带平滑动画
- **🔒 安全认证**: JWT Token 认证保护

### 访问 Web UI

```bash
# 启动服务后访问
docker-compose up -d

# 打开浏览器访问
http://localhost:8090  # 或你配置的 WEB_PORT

# 默认密码: admin123 (请在 .env 中修改)
```

---

## 系统架构

```
FreshRSS (标记番号)
    ↓
Workflow 1 (每10分钟)
    ↓
BitComet (下载)
    ↓
Workflow 2 (每30分钟)
    ↓
JavSP-Web (刮削整理)
    ↓
Jellyfin (媒体库)
    ↓
Workflow 3/4 (每小时)
    ↓
空间管理 & 清理
```

## 功能特性 ✅

### Workflow 1: 下载任务创建
- 自动从 FreshRSS 获取 Starred items
- **🆕 自动重试机制**：同时获取带有"源站抓取失败"标签的项目，定期重试抓取磁力链接
- 提取番号和磁力链接
- **🆕 JavBus 直抓 + RSSHub 回退**：当 FreshRSS 内容无磁力链接时，优先通过 JavBus AJAX 接口直抓，失败后再 fallback 到 RSSHub
- 去重检查（基于 content_id）
- 提交到 BitComet 下载
- 自动打标签："已开始下载"（提交时）/"下载完成"（完成时，同时移除"已开始下载"）/"已重复"/"下载错误"/"无磁力链接"/"源站抓取失败"
- 取消星标清理

### Workflow 2: 状态监控 & JavSP 提交 ⭐
- **三重任务匹配机制**：task_guid → task_id → 单独查询 API
- 实时更新下载状态（进度、速度、分享率、健康度）
- **提交前自动停止 BitComet 任务**（防止文件占用）
- **文件夹内容检查**（确保文件存在才提交）
- 自动提交 JavSP 刮削（满足 **可配置的分享率阈值** 或 **时间阈值**）
- **FreshRSS 标签切换**：添加"下载完成"，移除"已开始下载"

### Workflow 3: Jellyfin 空间管理
- 监控 Jellyfin 媒体库影片数量（**阈值可配置**）
- 自动删除最旧的影片（超过设定值时）
- 同步删除数据库记录
- **执行间隔可配置**（默认 60 分钟）

### Workflow 4: JavSP 整理检测 ⭐
- **双重检测机制**：scan_folder (优先) + 历史记录 (备用)
- 检测 JavSP 整理完成状态
- 自动删除 BitComet 任务和残留文件
- 更新数据库标记

---

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd av-download-manager

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

复制示例配置文件并修改：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写你的配置：

```env
# Database
DATABASE_URL=sqlite:///./data/av_downloads.db

# FreshRSS
FRESHRSS_URL=https://rss.your-domain.com
FRESHRSS_USERNAME=your_username
FRESHRSS_PASSWORD=your_password

# BitComet
BITCOMET_URL=http://your-server-ip:1235
BITCOMET_USERNAME=sandbox
BITCOMET_PASS=your_password
BITCOMET_DOWNLOAD_PATH=/home/sandbox/Downloads

# JavSP-Web
JAVSP_URL=https://jav.your-domain.com
JAVSP_USERNAME=your_username
JAVSP_PASSWORD=your_password
JAVSP_INPUT_PATH=/video/downloaded      # JavSP 输入目录 ⭐
JAVSP_OUTPUT_PATH=/video/output         # JavSP 输出目录（Jellyfin 媒体库）

# Jellyfin
JELLYFIN_URL=https://jellyfin.your-domain.com
JELLYFIN_API_KEY=your_api_key
JELLYFIN_LIBRARY_NAME=AV最新(自动化)

# Workflow 调度间隔
WORKFLOW1_INTERVAL_MINUTES=10
WORKFLOW2_INTERVAL_MINUTES=30
WORKFLOW3_INTERVAL_MINUTES=60

# 空间管理
MAX_COMPLETED_DOWNLOADS=50
MAX_RETRY_COUNT=3
```

### 3. 初始化数据库

```bash
python run.py --init-db
```

### 4. 启动

**方式一：启动调度器（生产模式）**

```bash
python run.py
```

**方式二：手动执行一次（测试模式）**

```bash
# 执行所有工作流
python run.py --once

# 只执行 Workflow 1
python run.py --once w1

# 只执行 Workflow 2
python run.py --once w2

# 执行 Workflow 3/4
python run.py --once w3
```

---

## Docker 部署（推荐）

项目使用 Docker Compose 一键部署完整链路，包含三个服务：
- **bitcomet**: 下载核心（`wxhere/bitcomet` 镜像，带 VNC）
- **javsp-web**: 刮削整理
- **av-download-manager**: 调度大脑

### 1. 配置环境

#### 命令行方式（推荐）

```bash
cp .env.example .env
# 编辑 .env，至少修改以下项：
#   VIDEO_PATH=你的宿主机视频目录
```

#### Synology Container Manager 方式

Container Manager **不支持 `--env-file` 参数**，请使用以下任一方案：

**方案 1（推荐）**: 重命名 `.env` 为 `.env`：
```bash
mv .env .env
```
Container Manager 导入时会自动读取 `.env` 文件。

**方案 2**: 使用 `docker-compose.container-manager.yml`：
- 已硬编码常用配置
- 只需要修改 volumes 中的宿主机路径
- 导入 Container Manager 即可

> ⚠️ **关于 BITCOMET_AUTHENTICATION**：
> BitComet WebUI 的 `/api/webui/login` 需要一个 `authentication` 字段。
> 该值由 `client_id + password` 派生，**没有公开算法**，通常需要通过浏览器 DevTools 抓包获取。
> 程序内置了一个旧版兼容值，如果登录失败，请：
> 1. 通过 VNC (http://宿主机IP:6080) 登录 BitComet 桌面版
> 2. 在浏览器中打开 BitComet WebUI (http://your-server-ip:1235)
> 3. 抓包 `/api/webui/login` 请求，复制 `authentication` 值
> 4. 填入 `.env` 的 `BITCOMET_AUTHENTICATION=` 中

### 2. 启动服务

```bash
# 构建并启动全部服务
docker-compose up -d

# 初始化数据库（首次运行）
docker-compose exec av-download-manager python run.py --init-db

# 查看日志
docker-compose logs -f av-download-manager

# 停止服务
docker-compose down
```

### 4. 路径映射说明

`VIDEO_PATH` 是宿主机上的统一视频根目录，三个服务通过不同子路径共享：

| 宿主机路径 | 容器 | 容器内路径 | 用途 |
|-----------|------|-----------|------|
| `${VIDEO_PATH}/downloaded` | bitcomet | `/home/sandbox/Downloads` | BitComet 下载目录 |
| `${VIDEO_PATH}/downloaded` | av-download-manager | `/home/sandbox/Downloads` | AV-DM 探测文件用 |
| `${VIDEO_PATH}` | javsp-web | `/video` | JavSP 工作目录 |
| `${VIDEO_PATH}` | av-download-manager | `/video` | AV-DM 路径转换用 |

### 5. 访问入口

| 服务 | 地址 | 说明 |
|------|------|------|
| **Web UI** | `http://宿主机IP:8090` | **AV Download Manager 管理界面** ⭐ |
| BitComet VNC | `http://宿主机IP:6080` | 桌面版 BitComet，可在这里开启 1235 远程端口 |
| JavSP-Web | `http://宿主机IP:8090` (注意端口冲突，需修改) | 刮削管理界面 |
| BT 监听端口 | `宿主机IP:6082` | TCP/UDP |

### 6. 配置管理（新功能）

Web UI 提供完整的配置管理功能：

#### 实时配置修改
- **服务连接配置**：FreshRSS、RSSHub、BitComet、JavSP-Web、Jellyfin
- **业务配置**：工作流间隔、JavSP 提交条件、路径设置
- **修改后立即生效**，无需重启容器

#### 服务连接测试
每个服务都支持**一键测试连接**：
1. 打开 Web UI → 设置 → 配置服务连接
2. 填写服务信息
3. 点击 **"测试连接"** 按钮
4. 查看测试结果（成功/失败及详细错误信息）

#### 配置备份/恢复
- **创建备份**：一键备份当前配置
- **恢复配置**：从历史备份恢复
- **导出配置**：下载完整配置 JSON

#### 配置热加载
- 通过 Web UI 修改的配置会立即保存到 `app.env`
- 所有工作流会自动使用新配置
- 手动修改 `app.env` 后也会自动重新加载

### 5. 网络说明

采用混合网络架构：

| 组件 | 网络类型 | 访问方式 |
|------|---------|---------|
| BitComet | Macvlan（独立 IP）| `http://your-server-ip:1235` |
| JavSP-Web | Docker bridge (`av-net`) | `http://javsp-web:8090` |
| AV-DM | Docker bridge (`av-net`) | - |

**BitComet 网络详情**：
- 使用 Macvlan 网络 `bitcomet-direct`，拥有独立 IP 地址
- IPv4: `your-server-ip` / IPv6: `your-ipv6-address`
- 所有端口直接暴露在独立 IP 上（无需端口映射）

> **注意**：`1235` 是 BitComet 远程访问（WebUI）端口，需在 VNC 界面中手动启用。

---

## 项目结构

```
av-download-manager/
├── app/
│   ├── __init__.py
│   ├── config.py          # 配置管理 (Pydantic Settings)
│   ├── database.py        # 数据库模型 (SQLAlchemy)
│   ├── logger.py          # 日志配置 (Loguru)
│   ├── main.py            # 主程序入口
│   ├── services/          # API 客户端
│   │   ├── base.py        # HTTP 基类
│   │   ├── freshrss.py    # FreshRSS API
│   │   ├── bitcomet.py    # BitComet API ⭐
│   │   ├── javsp.py       # JavSP-Web API ⭐
│   │   └── jellyfin.py    # Jellyfin API
│   └── workflows/         # 工作流实现
│       ├── download.py    # Workflow 1
│       ├── monitor.py     # Workflow 2 ⭐
│       └── cleanup.py     # Workflow 3 & 4 ⭐
├── data/                  # 数据库文件
│   └── av_downloads.db
├── logs/                  # 日志文件
│   └── app.log
├── tests/                 # 测试代码
├── .env.example           # 环境变量示例
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── run.py                 # 启动脚本
└── README.md
```

---

## 配置说明

### Web UI 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WEB_PORT` | 8090 | Web UI 访问端口（宿主机映射） |
| `WEB_PASSWORD` | admin123 | 登录密码（**请修改默认值**） |
| `WEB_SECRET_KEY` | - | JWT 密钥（用于生成登录令牌） |
| `API_PORT` | 8080 | FastAPI 调试端口（可选） |

### 核心配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | sqlite:///./data/av_downloads.db | 数据库连接 |
| `LOG_LEVEL` | INFO | 日志级别 (DEBUG/INFO/WARNING/ERROR)，见下方日志系统说明 |

### 服务配置

| 变量 | 说明 | 示例 |
|------|------|------|
| `FRESHRSS_URL` | FreshRSS 地址 | `https://rss.example.com` |
| `JAVBUS_BASE_URL` | JavBus 地址（可选，用于磁力链接直抓） | `https://www.javbus.com` |
| `RSSHUB_BASE_URL` | RSSHub 地址（可选，用于 JavBus 直抓失败后的回退） | `https://rsshub.example.com:8888` |
| `BITCOMET_URL` | BitComet WebUI 地址 | `https://bit.example.com:8888` |
| `BITCOMET_DOWNLOAD_PATH` | BitComet 下载目录 | `/home/sandbox/Downloads` |
| `JAVSP_URL` | JavSP-Web 地址 | `https://jav.example.com` |
| `JAVSP_INPUT_PATH` | JavSP 输入目录 ⭐ | `/video/downloaded` |
| `JAVSP_OUTPUT_PATH` | JavSP 输出目录 | `/video/output` |
| `JELLYFIN_URL` | Jellyfin 地址 | `https://jellyfin.example.com` |
| `JELLYFIN_API_KEY` | Jellyfin API Key | - |

### 工作流配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WORKFLOW1_INTERVAL_MINUTES` | 10 | Workflow 1 执行间隔（分钟） |
| `WORKFLOW2_INTERVAL_MINUTES` | 30 | Workflow 2 执行间隔（分钟） |
| `WORKFLOW3_INTERVAL_MINUTES` | 60 | Workflow 3/4 执行间隔（分钟） |
| `MAX_COMPLETED_DOWNLOADS` | 50 | 最大保留完成下载数 |
| `MAX_RETRY_COUNT` | 3 | JavSP 提交最大重试次数 |
| `JAVSP_SUBMIT_SHARE_RATIO` | 2.0 | JavSP 提交分享率阈值（2.0 = 200%） |
| `JAVSP_SUBMIT_HOURS` | 6 | JavSP 提交时间阈值（小时） |

---

## 完整流程测试 ✅ 2026-04-01

### PAKO-101 端到端测试成功

```
测试番号: PAKO-101
BitComet 任务: 1013 (task_guid: bt_865d42536d2201fae22ac881c0d864942f9de6ef)

完整流程:
├── Workflow 1 (模拟)
│   ├── 创建数据库记录: ✅
│   ├── BitComet 任务绑定: ✅ task_id=1013
│   └── 状态: running
│
├── Workflow 2 执行
│   ├── 任务匹配: ✅ 通过单独查询 API (task_list 不返回 stopped 任务)
│   ├── 状态更新: ✅
│   │   ├── 进度: 100.0%
│   │   ├── 分享率: 1.7
│   │   ├── 状态: stopped
│   │   └── 文件数: 2
│   ├── 提交条件: ✅ 已创建 7.0 小时 > 6小时
│   ├── FreshRSS 标签: ✅ "下载完成"
│   ├── 停止 BitComet: ✅ POST /api_v2/tasks/action {action: "stop"}
│   ├── 文件夹检查: ✅ scan_folder count=1
│   └── JavSP 提交: ✅ 任务创建成功
│
├── JavSP 整理
│   └── 整理完成: ✅ 原文件夹已删除
│
└── Workflow 4 执行
    ├── 检测任务: ✅ PAKO-101
    ├── 方式1 scan_folder: ✅ count=0 (文件夹已空)
    ├── 方式2 历史记录: ✅ 确认整理成功
    ├── BitComet 删除: ✅ 任务 1013 已删除
    └── 数据库更新: ✅ javsp_checked=True, folder_cleaned=True

最终结果: 全流程测试通过！🎉
```

---

## 关键特性说明

### 1. 三重任务匹配机制 ⭐

Workflow 2 使用三种方式匹配 BitComet 任务：

| 优先级 | 方式 | API | 说明 |
|--------|------|-----|------|
| 1 | `task_guid` | `/api_v2/task_list/get` | 不变标识，最可靠 |
| 2 | `task_id` | `/api_v2/task_list/get` | 动态分配，备用 |
| 3 | `task_summary` | `/api/task/summary/get` | 单独查询，解决 task_list 不全问题 |

**为什么需要单独查询？**
- `task_list/get` 默认不返回做种/上传中的任务
- 已停止的任务需要从单独接口查询

### 2. 提交前自动停止任务 ⭐

Workflow 2 在提交 JavSP 前自动停止 BitComet 任务：

```python
# 1. 停止 BitComet 任务（防止文件被占用）
POST /api_v2/tasks/action
{"task_ids": ["1013"], "action": "stop"}

# 2. 动态探测实际媒体目录（基于番号精确匹配）
find_actual_media_folder(base_path, content_id="PAKO-101")
# 处理如 "madoubt.com 228563.xyz KNB-406" → 匹配到 KNB-406

# 3. 检查文件夹内容
GET /api/tasks/fs/scan?path=/video/downloaded/PAKO-101

# 4. 提交 JavSP
POST /api/tasks/manual
{"input_directory": "/video/downloaded/PAKO-101"}
```

**动态探测逻辑**：
- 传入 `content_id`（番号）进行精确匹配
- 规范化文件夹名（去掉域名前缀如 `madoubt.com`）
- **双重检测机制**：
  - 方式1：去掉"-"匹配（如 `KNB-406` 匹配 `KNB406`、`KNB-406-CD1`）
  - 方式2："-"前后分开匹配（如 `KNB-406` 需同时匹配 `KNB` 和 `406`，避免部分匹配）

### 3. 双重整理检测机制 ⭐

Workflow 4 使用两种方式检测 JavSP 整理完成：

| 优先级 | 方式 | 判断条件 |
|--------|------|----------|
| 1 | `scan_folder` | `count == 0` → 文件夹已空，整理完成 |
| 2 | `历史记录` | `cover_download_success` → 确认成功 |

**为什么需要两种方式？**
- **scan_folder**: JavSP 整理单文件任务后会删除整个文件夹
- **历史记录**: 备用确认，确保 JavSP 确实成功处理

### 4. JavBus 磁力链接直抓 + RSSHub 回退 ⭐

当 FreshRSS 条目中**没有磁力链接**时，Workflow 1 会按以下优先级尝试抓取：

```
FreshRSS 条目 (内容无磁力)
    ↓
提取番号: SABA-975
    ↓
├─ 第1步: JavBus 直抓
│   访问页面 → 提取 gid/uc → 调用 AJAX 接口获取磁力链接
│   成功 → 正常下载流程
│   失败 → 继续下一步
│
└─ 第2步: RSSHub 回退 (fallback)
    构造 RSSHub URL: https://rsshub.example.com/javbus/home/ja/SABA-975
    抓取 RSS 内容 → 提取磁力链接
    成功 → 正常下载流程
    失败 → 标记 "源站抓取失败"
```

**为什么需要 JavBus 直抓？**
- JavBus 新片的磁力链接是**动态 AJAX 加载**的，RSSHub 只能解析静态 HTML
- RSSHub 在解析新片时，可能错误地抓到页面底部"相关推荐"中的其他番号磁力链接
- 这会导致 ADM 下载了错误的影片（番号对但磁力链接是其他影片）
- JavBus 直抓通过调用真实的 AJAX 接口 (`ajax/uncledatoolsbyajax.php`)，能获取准确的磁力链接

**DN 校验（番号匹配校验）**
- 无论是 JavBus 还是 RSSHub 返回的磁力链接，都会检查 `dn` 参数是否包含目标番号
- 如果抓到的磁力链接对应其他明确番号，ADM 会**拒绝使用**该链接，避免下载错误影片
- 拒绝后会标记为 `"源站抓取失败"`，等待下次重试

**配置要求：**
```env
# JavBus 直抓（默认 https://www.javbus.com，如有反代可修改）
JAVBUS_BASE_URL=https://www.javbus.com

# RSSHub 回退（可选）
RSSHUB_BASE_URL=https://rsshub.your-domain.com
```

**标签说明：**
- `源站抓取失败` - JavBus 和 RSSHub 均抓取失败，或抓到的磁力链接 dn 不匹配目标番号（会被定期重试）
- `无磁力链接` - 没有 JavBus/RSSHub 配置或无法构造抓取 URL

### 5. 自动重试机制 ⭐

Workflow 1 会**定期重试**之前抓取磁力链接失败的项目：

```
工作流程：
1. 获取 Starred items（正常流程）
2. 同时获取带有"源站抓取失败"标签的项目（重试流程）
3. 对重试项目：
   - 再次尝试从 RSSHub 抓取磁力链接
   - 如果抓取成功 → 移除"源站抓取失败"标签，添加"已开始下载"标签，提交下载
   - 如果抓取失败 → 保持现状，下次继续重试
```

**为什么需要这个功能？**
- 某些 RSS 源的磁力链接可能有延迟更新
- 自动重试无需人工干预，提高成功率
- 保持"源站抓取失败"标签的项目会持续被重试，直到成功或手动处理

**重试条件：**
- 项目带有 `"源站抓取失败"` 标签
- 数据库中不存在该番号的记录（未下载过）
- 每次 Workflow 1 执行时自动重试（默认每 10 分钟）

### 6. 路径配置分离

支持 BitComet 和 JavSP 使用不同路径（适用于 Docker 多容器场景）。
**关键原则：`BITCOMET_DOWNLOAD_PATH` 和 `JAVSP_INPUT_PATH` 必须映射到同一个宿主机物理目录**，否则 JavSP 无法读取 BitComet 下载的文件。

**实际部署示例（QNAP NAS）：**
```
BitComet 容器 volume: /path/to/your/video/folder/downloaded:/home/sandbox/Downloads
JavSP 容器 volume:    /path/to/your/video/folder/downloaded:/video/downloaded
JavSP 容器 volume:    /path/to/your/video/folder:/video
```

对应配置：
```env
BITCOMET_DOWNLOAD_PATH=/home/sandbox/Downloads
JAVSP_INPUT_PATH=/video/downloaded
JAVSP_OUTPUT_PATH=/video/output
```

### 7. 三层日志系统 ⭐

日志系统采用分层架构，满足不同场景需求：

```
Container Manager (控制台)
├─ INFO模式: 简洁输出，一眼看懂
│   18:30:45 | ▶️  W1-下载任务
│   18:30:46 | ⬇️  开始下载: ABC-123
│   18:30:47 | ✅ W1-下载任务 完成 | started=2
│
└─ DEBUG模式: 详细输出，包含模块/行号
    2026-04-05 18:30:45 | INFO    | download:117 | ...

日志文件 (logs/app.log)
始终详细，包含时间/级别/模块/行号，供查错
```

**配置方式：**
```env
# 简洁日志（推荐生产环境）
LOG_LEVEL=INFO

# 详细日志（推荐调试）
LOG_LEVEL=DEBUG
```

**快捷日志图标说明：**
- `▶️ ` 工作流开始
- `✅` 工作流完成
- `⬇️ ` 开始下载
- `✓` 下载完成
- `📁` 提交刮削
- `🗑️ ` 清理完成
- `✗` 错误
- `⚠️ ` 警告

---

## 数据库模型

**DownloadRecord** 表：

| 字段 | 类型 | 说明 |
|------|------|------|
| content_id | String(50) | 番号，如 300MIUM-1334 |
| content_title | String(500) | 完整标题 |
| magnet_url | String(1000) | 磁力链接 |
| freshrss_item_id | String(200) | FreshRSS 条目 ID |
| bitcomet_task_id | String(50) | BitComet 任务 ID（动态）|
| bitcomet_task_guid | String(100) | BitComet 任务 GUID（不变）|
| status | String(20) | pending/running/completed/error/javsp_error |
| share_ratio | Float | 分享率 |
| progress | Integer | 进度（千分比，1000=100%）|
| javsp_task_id | String(100) | JavSP 任务 ID |
| javsp_checked | Boolean | 是否已检测整理状态 |
| folder_cleaned | Boolean | 文件夹是否已清理 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

---

## 故障排查

### 任务匹配失败

**现象**: Workflow 2 提示 "BitComet 任务不存在"

**解决**:
1. 检查 `task_guid` 是否正确保存到数据库
2. 确认任务在 BitComet 中存在
3. 查看日志中的匹配过程（三种方式都会尝试）

### JavSP 提交失败

**现象**: "文件夹为空或不存在"

**解决**:
1. 检查 `JAVSP_INPUT_PATH` 配置是否正确
2. 确认文件夹存在且不为空
3. 检查 BitComet 任务是否已停止（文件不能被占用）
4. 检查 `save_folder` 和实际文件夹名是否匹配（大小写/前缀差异）

### 标签没打上

**现象**: FreshRSS 中看不到标签

**解决**:
1. 检查 FreshRSS 登录是否正常
2. 确认 `freshrss_item_id` 正确保存
3. 刷新浏览器页面（可能是缓存）

---

## 开发

```bash
# 代码格式化
black app/

# 代码检查
ruff check app/
mypy app/

# 运行测试
pytest tests/
```

---

## 许可证

MIT License

---

---

## API 文档

Web UI 基于 RESTful API 构建，API 文档可通过以下方式查看：

### 启动后访问 Swagger UI

```
http://localhost:8080/docs
```

### 主要 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/login` | POST | 用户登录 |
| `/api/v1/tasks` | GET | 获取任务列表 |
| `/api/v1/tasks/{id}` | GET | 获取任务详情 |
| `/api/v1/tasks/{id}/retry` | POST | 重试任务 |
| `/api/v1/stats` | GET | 获取统计信息 |
| `/api/v1/workflows` | GET | 获取工作流状态 |
| `/api/v1/workflows/{name}/trigger` | POST | 触发工作流 |
| `/api/v1/logs` | GET | 获取日志 |
| `/api/v1/config` | GET | 获取配置 |
| `/api/v1/config` | PUT | **更新配置（实时生效）** |
| `/api/v1/config/backup` | POST | **创建配置备份** |
| `/api/v1/config/restore` | POST | **恢复配置备份** |
| `/api/v1/services/status` | GET | **获取所有服务状态** |
| `/api/v1/services/test/freshrss` | POST | **测试 FreshRSS 连接** |
| `/api/v1/services/test/rsshub` | POST | **测试 RSSHub 连接** |
| `/api/v1/services/test/bitcomet` | POST | **测试 BitComet 连接** |
| `/api/v1/services/test/javsp` | POST | **测试 JavSP 连接** |
| `/api/v1/services/test/jellyfin` | POST | **测试 Jellyfin 连接** |

---

**项目状态**: ✅ 完整流程测试通过，已就绪 for 生产环境

**最新功能**: JavBus 直抓 + DN 校验（2026-04-17）- 修复 RSSHub 抓取到错误番号磁力链接的问题

*最后更新: 2026-04-20* (新增 Web UI 深色模式与主题切换)
