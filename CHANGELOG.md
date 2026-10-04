# 变更记录

本文件按 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 的组织方式记录变更。

> **尚未发布任何版本。** 没有公开仓库、没有 Release、没有已跑绿的 CI，开源许可也尚未确认（见 [docs/PROVENANCE.md](./docs/PROVENANCE.md)）。下面只记录本地导出基线的整理内容。

## [Unreleased]

### Added

- 从本机在用的 `hxz-content-reach` 技能导出**单篇视频默认链路**的工程化副本：采集、查重、下载、转写、标点、写入飞书与精确回读。
- 可配置化：飞书目标与本机工具路径改由配置提供（`config.local.json` / `XHS_*` 环境变量 / `$XHS_CONFIG_FILE`），不再写死在代码里。
- `doctor` 子命令：离线自检，列出配置与路径存在性，缺必需项时非零退出，不联网。
- 中文 `README.md` 与英文 `README.en.md`，边界一致。
- 静态纯 SVG 门面：`assets/readme/hero.svg`、`assets/readme/workflow.svg`。
- 文档：`docs/INSTALL.md`、`docs/CONFIGURATION.md`、`docs/VERIFICATION.md`、`docs/ARCHITECTURE.md`、`docs/PROVENANCE.md`。
- 社区文件：`CONTRIBUTING.md`、`SECURITY.md`、`CHANGELOG.md`，以及 `.github/` 下的 issue / PR 模板。
- 离线 CI 工作流草稿（Windows + Ubuntu）：单元测试、`compileall`、`node --check`；不含任何密钥，不访问真实浏览器或飞书。

### Changed

- 移除了导出范围之外的旧分支：Apple Silicon Mac 的 MLX 视频链路、图文/主页批量与 Markdown 归档流程。
- 去除了登录凭据、浏览器 Profile、`.env`、密钥、媒体、逐字稿与旧案例内容。

### Notes

- 本仓库的离线测试与 CI 只是**本地准备**，未在任何远程 CI 上运行过，因此不构成“CI 已通过”的声明。
- 整条实时链路（全新会话 + 新视频 + 使用者自己的飞书表）**尚未验收**；“已回读通过”来自导出前的原版基线。
- README 视觉验收只做了本地渲染检查（桌面 900px / 移动 360px），未代表在 GitHub 上的实际渲染已验收。
