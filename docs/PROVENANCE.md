# 来源与授权边界（PROVENANCE）

本目录已整理为私有仓库。公开或再许可前，需确认所有内容的来源授权；本项目不授予 MIT 许可。

## 1. 来源

- 前端来源包：`hongshu`（见 `SKILL.md` frontmatter 的 `metadata.origin`）。
- 上游技能：`hxz-content-reach`，本导出只保留其「单篇视频默认链路」，去掉了 Apple Silicon Mac 的 MLX 视频链路、图文/主页批量与 Markdown 归档旧流程，以及登录/Profile/.env/秘钥/媒体/逐字稿/旧案例内容。

## 2. 默认链路的文件构成

**本次自研核心（复用）**，均按本项目的可配置契约做了最小改造：

| 文件 | 说明 |
|---|---|
| `scripts/xhs_pipeline.py` | 命令入口；本次新增配置加载、`doctor`、`main()`，并在 fetch/push 写入前校验必需配置 |
| `scripts/product_rules.py` | 字段/查重/回读/写入状态规则（基本原样） |
| `scripts/punctuate.py` | 标点步骤；模型路径改由 `XHS_PUNCT_MODEL` 提供 |
| `scripts/xhs_collect.mjs` | 小红书 CDP 页面采集（原样） |
| `scripts/douyin_collect.mjs` | 抖音 CDP 采集（同一管线的次要平台，原样） |
| `scripts/xhs_config.py` | 新增：配置解析（环境变量 > 配置文件 > PATH 默认） |
| `scripts/transcribe.py` | 原在整个 IDE 工具目录（`reach-whisper-venv/transcribe.py`），本次打包进 `scripts/` 并去掉硬编码的缓存/模型路径 |

**本导出新增的产品化文件**：`tests/*`（从原 44+ 单测改写为纯离线、可携带、配置契约化）、`config.example.json`、`requirements.txt`、`.gitignore`、`SKILL.md`、`docs/*`、`THIRD_PARTY_NOTICES.md`、`LICENSES/`。

## 3. 本地工具依赖（都不随本目录分发）

- **faster-whisper**（ASR 运行时）：pip 依赖，见 `requirements.txt`。
- **sherpa-onnx + CT-Transformer ONNX**（标点运行时）：pip 依赖 + 本机预置模型文件；权重不进 Git。
- **ffmpeg / ffprobe**：外部二进制。
- **Node.js**：跑 `.mjs` 采集脚本。
- **lark-cli**：外部飞书 CLI（MIT，见 `LICENSES/LARK-CLI-MIT.txt`）。

## 4. 授权边界

- 上游来源包的 `THIRD_PARTY_NOTICES` 覆盖的是那个工具箱里的其他第三方 Skill，**并不授权本 Skill 的全部内容**；因此本目录**不**为一个新许可证背书，也没有套用 MIT 等公开许可证。
- 本项目不授予 MIT 许可；公开或再许可前，需确认所有内容的来源授权。
- 复用的自研代码保留其来源说明；对运行时真正依赖的第三方，`THIRD_PARTY_NOTICES.md` 按实际依赖列出并注明许可；原许可证通知在有必要处保留（如 `LICENSES/LARK-CLI-MIT.txt`）。
- 真实飞书 base/table/record、样本笔记 ID、媒体与逐字稿均未进入本目录；配置只留占位符。
