# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-04-22

### Added
- **Web UI 完整移动端适配**：支持手机 Safari、Chrome 等浏览器访问。
  - 布局适配：侧边栏在屏幕宽度 < 768px 时自动变为左侧抽屉菜单，顶部 Header 添加汉堡按钮。
  - 仪表盘：统计卡片保持响应式，工作流/活动表格区域支持横向滚动，磁盘信息在移动端垂直堆叠。
  - 任务管理：搜索/筛选/刷新操作区域在移动端垂直堆叠，任务表格支持横向滚动，任务详情抽屉宽度调整为 85%。
  - 日志查看：筛选区域移动端适配，日志容器高度优化为 `50vh`。
  - 系统设置：所有配置对话框（服务连接/业务配置/Web UI/备份管理）在移动端自动调整为 `95%` 宽度。
  - 登录页：卡片宽度自适应，标题字体微调。

### Fixed
- **登录页回车键行为**：修复输入密码后按回车键刷新页面而非登录的问题。通过在 `el-form` 上添加 `@submit.prevent` 阻止表单默认提交行为。

## [0.3.0] - 2026-04-21

### Added
- **磁力链接种子文件自动获取**：通过 `itorrents.org` 在线缓存服务自动获取 `.torrent` 文件。
  - 支持本地缓存（`data/torrents/`），避免重复请求。
  - 备选 `libtorrent` P2P 获取（在线缓存失败时）。
- **广告文件智能过滤**：创建任务时自动过滤广告文件。
  - 禁用非视频扩展名（.url / .html / .txt / .apk / .chm / .zip / .exe）。
  - 禁用小视频文件（< 100MB 的广告视频）。
  - 保留主视频和所有 VR 多分卷视频（PART1/2/3、-A/-B/-C 等）。
- **BitComet API 扩展**：新增 `get_task_files()` 和 `set_file_priority()` 接口。
- **Workflow 1 增强**：下载流程改为"磁力链接 → 获取种子 → 过滤广告 → 创建任务 → 设置优先级"。

### Changed
- `BitCometClient.add_task()` 支持 `torrent_file` 参数。
- 新增依赖 `libtorrent>=2.0.0`。

## [0.2.0] - 2026-04-20

### Added
- **Web UI 深色模式（Dark Mode）**：完整支持浅色/深色主题切换。
  - 顶部 Header 新增 🌙/☀️ 一键切换按钮，切换时带 0.3s 平滑颜色过渡动画。
  - 深色配色参考 GitHub Dark / Vercel Dark，背景层次：`#0d1117` → `#161b22` → `#21262d`。
  - 所有 Element Plus 组件（卡片、表格、表单、对话框、抽屉、标签页、分页等）已完整适配深色样式。
  - 统计卡片采用渐变背景 + 悬停缩放动效，深色模式下更醒目。
  - 日志终端区支持浅色/深色两套配色方案（浅色 → 浅色终端风格，深色 → VS Code Dark+ 风格）。
  - 状态标签（StatusBadge）在深色模式下自动使用高饱和度配色，保证可读性。
  - 登录页深色模式采用深邃渐变背景，与浅色模式的紫渐变形成对比。
- **主题系统架构**：基于 CSS 变量 + Pinia Store 的主题管理系统。
  - `web/src/styles/theme.css`：定义浅色/深色两套完整的 CSS 变量，覆盖布局、背景、文字、边框、阴影等。
  - `web/src/stores/theme.ts`：主题状态管理，支持 localStorage 持久化、系统主题自动检测、实时切换。
  - 首次访问自动跟随系统主题偏好，手动切换后记住用户选择。

### Changed
- 侧边栏菜单项增加圆角（`border-radius: 8px`）和间距优化，现代感更强。
- 统计卡片、磁盘信息卡片、日志卡片统一使用 `border-radius: 12px`，视觉更柔和。
- `.gitignore` 新增 `web/node_modules/`，防止本地前端依赖误提交。

## [0.1.3] - 2026-04-19

### Added
- **磁力链接智能选择**：从多个磁力链接中按规则选择最佳链接。
  - P1 优先级（无码/破解/流出）：文件名含 `-U`, `-AI`, `-UC`, `-UNCENSORED`, `-UNCEN`, `-UNCENS`, `-LEAK`, `-LEAKED` 或 `uncensored`/`uncensored leak` 关键词。
  - P2 优先级（中文字幕）：文件名含 `-C`, `-CH`, `-CN`。
  - 同优先级内按分享日期升序 → 文件大小升序选择。
  - 兜底：无特殊后缀时选择日期最新且大小最小的。
- **番号识别扩展**：参考 JavSP 项目，新增支持 15 种番号格式。
  - FC2, HEYDOUGA, GETCHU, GYUTTO, 259LUXU, MUGEN, IBW
  - 东热 RED/SKY/EX 系列、TMA、N/K 系列、R18、纯数字无码等。
- **JavBus AJAX 兼容性**：支持解析无 `<table>` 包裹的纯 `<tr>` 行片段（JavBus AJAX 接口返回格式）。

### Changed
- `_extract_magnet()` 保持接口不变，内部新增 `_extract_all_magnets()` + `_select_best_magnet()` 逻辑。
- 优先从 HTML 表格解析全部磁力链接，失败时 fallback 到原有正则提取。

## [0.1.2] - 2026-04-17

## [0.1.2] - 2026-04-17

### Fixed
- **磁力链接番号不匹配问题**：RSSHub 在解析新片时，可能抓取到页面底部"相关推荐"中的错误番号磁力链接，导致下载了错误的影片。
  - 新增 **JavBus 直抓机制**：优先通过 JavBus AJAX 接口 (`ajax/uncledatoolsbyajax.php`) 抓取磁力链接，准确率更高。
  - 新增 **磁力链接 DN 校验**：提取到的磁力链接必须匹配目标番号才使用，否则拒绝下载并标记为"源站抓取失败"。
  - RSSHub 改为 JavBus 失败后的 fallback 机制。

### Technical Details
- JavBus 直抓通过提取页面 HTML 中的 `gid` 和 `uc` 参数调用 AJAX 接口。
- 针对 JavBus 的年龄验证 302 响应，关闭 httpx 自动重定向以正确读取响应体中的 `gid`。
- 新增 `JAVBUS_BASE_URL` 配置项（默认 `https://www.javbus.com`）。

## [0.1.1] - 2026-04-15

### Fixed
- Fixed content ID extraction to support numeric prefixes (e.g. `200GANA-3370` was incorrectly extracted as `GANA-3370`). This affected both FreshRSS RSSHub fallback and cleanup workflow matching.

## [0.1.0] - 2026-04-13

### Added
- **Web UI Management Interface**: Built with Vue 3 + Element Plus + Vite.
  - Dashboard with real-time task statistics, disk usage, and workflow status.
  - Task management with filtering, searching, retry, cancel, and delete operations.
  - Log viewer with real-time streaming, level filtering, and keyword search.
  - System settings with live configuration updates, service connection testing, and backup/restore.
- **Dynamic Configuration Management**:
  - Separated Docker configuration (`.env`) from application configuration (`app.env`).
  - Supports hot-reloading of `app.env` without restarting the container.
  - Configuration backup and restore via Web UI.
- **Workflow 1 - Download Task Creation**:
  - Automatically fetches FreshRSS starred items and extracts content IDs.
  - RSSHub fallback for magnet links when FreshRSS content is incomplete.
  - Automatic retry mechanism for items tagged "source fetch failed".
  - Submits download tasks to BitComet and manages FreshRSS tags.
- **Workflow 2 - Status Monitoring & JavSP Submission**:
  - Triple task matching mechanism (`task_guid` → `task_id` → `task_summary`).
  - Automatic JavSP scraping submission based on configurable share ratio or time thresholds.
  - Download timeout detection (default 48 hours) with automatic BitComet task stopping.
- **Workflow 3 - Jellyfin Space Management**:
  - Monitors Jellyfin library size and automatically deletes oldest items when exceeding limits.
- **Workflow 4 - JavSP Completion Detection & Cleanup**:
  - Dual detection mechanism (`scan_folder` + history record) for determining completion.
  - Automatically deletes BitComet tasks and cleans residual folders.
- **Workflow 4b - Timeout Task Handling**:
  - Supports manual third-party downloads (e.g., Thunder) for timeout tasks and auto-submits to JavSP.
- **Three-tier Logging System**:
  - Console: concise output for INFO, detailed for DEBUG.
  - File logs: always detailed with module/line numbers for troubleshooting.

### Fixed
- Fixed BitComet `save_folder` whitelist restriction by using root directory with dynamic subfolder detection.
- Fixed task matching failures by prioritizing `task_guid` over `task_id`.
- Fixed JavSP submission to incorrect folders via precise content-ID matching with dual verification.

### Technical Details
- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, APScheduler.
- **Frontend**: Vue 3, TypeScript, Element Plus, Pinia.
- **Database**: SQLite with connection pooling.
- **Deployment**: Docker Compose with multi-service architecture.

[Unreleased]: https://github.com/han0x0/av-dm/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/han0x0/av-dm/releases/tag/v0.2.0
[0.1.3]: https://github.com/han0x0/av-dm/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/han0x0/av-dm/releases/tag/v0.1.2
[0.1.1]: https://github.com/han0x0/av-dm/releases/tag/v0.1.1
[0.1.0]: https://github.com/han0x0/av-dm/releases/tag/v0.1.0
