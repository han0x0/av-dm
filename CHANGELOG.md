# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions workflow for automatically building and pushing Docker images to ghcr.io.
- Support for multi-arch Docker images (`linux/amd64`, `linux/arm64`).
- `latest`, `main`, and SemVer (`X.Y.Z`, `X.Y`, `X`) Docker image tags.

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

[Unreleased]: https://github.com/han0x0/av-dm/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/han0x0/av-dm/releases/tag/v0.1.2
[0.1.1]: https://github.com/han0x0/av-dm/releases/tag/v0.1.1
[0.1.0]: https://github.com/han0x0/av-dm/releases/tag/v0.1.0
