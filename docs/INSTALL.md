# 安装与依赖

本 Skill 是用于处理单篇小红书或抖音视频并写入飞书多维表格的本地工作流。它不会自动登录；首次准备依赖时，Agent 会先检查本机环境，说明所需软件、模型用途和保存位置，并经用户确认后再安装软件或下载模型。工具运行本身不会隐式安装依赖或下载模型。安装 Skill 指的是把本目录放到 `SKILL_DIR`，并把下面「已有资源」的路径通过配置指过去。

## 1. 运行环境

- 本导出在 **Windows 11 + Git Bash** 上实测（原生程序用 `D:/...` 正斜杠路径）。Linux/macOS 未验证。
- `python`（Windows 上 `python3` 常是微软商店占位符，用 `python`）。
- `node`（采集脚本 `scripts/xhs_collect.mjs`、`douyin_collect.mjs` 依赖 Node 的全局 `fetch`/`WebSocket`，需较新的 Node）。
- 外部二进制的 `ffmpeg` / `ffprobe`（放音频、探测音轨、转封面）。它们不是 pip 包。

## 2. 本 Skill 自带

- `scripts/xhs_pipeline.py`：命令入口（`doctor` / `fetch` / `push` / `repair`）。
- `scripts/xhs_config.py`：配置解析（环境变量 > 配置文件 > PATH 默认）。
- `scripts/product_rules.py`：字段规则、查重/回读校验、写入状态。
- `scripts/transcribe.py`：本地 faster-whisper 转写（走已有 ASR venv）。
- `scripts/punctuate.py`：本地 CT-Transformer 标点（只加标点，改字则拒绝）。
- `scripts/xhs_collect.mjs`、`scripts/douyin_collect.mjs`：CDP 页面采集。

## 3. 已有资源（需要你自己准备并配置路径）

- **飞书 CLI**：`lark-cli`（`--as user` 身份）。默认从 PATH 查找，可用 `XHS_LARK_CLI` 指定。
- **ASR venv**：一个已装好 `requirements.txt` 的 Python 环境，用它的解释器跑 `transcribe.py` / `punctuate.py`。用 `XHS_WHISPER_PYTHON` 指向 `.../Scripts/python.exe`。
- **Whisper 模型**：`XHS_WHISPER_MODEL` 指向已有模型（默认名 `large-v3-turbo`），缓存目录用 `XHS_HF_HOME`。权重不进 Git。
- **标点模型**：CT-Transformer ONNX，用 `XHS_PUNCT_MODEL` 指向。缺省时不内置模型，`punctuate.py` 会明确报错。
- **Chrome**：带窗口的真实 Chrome 与一个专用 Profile。用 `XHS_CHROME_PATH` / `XHS_CHROME_PROFILE` 指定；`XHS_CDP_PORT` 指定调试端口（默认 9333）。

安装本机依赖（在你自己的 venv 里，本 Skill 不代跑）：

```bash
python -m venv D:/path/to/asr-venv
D:/path/to/asr-venv/Scripts/python.exe -m pip install -r requirements.txt
```

## 4. 配置与自检

复制 `config.example.json` 为 `config.local.json`（已被 `.gitignore` 忽略），填入你自己的 base/table/路径；或用环境变量覆盖。然后：

```bash
python "$SKILL_DIR/scripts/xhs_pipeline.py" doctor
```

`doctor` 输出缺项与路径存在性；缺 `base_token` / `table_id`（含未替换的示例占位 `YOUR_*`）或核心工具路径（`lark_cli` / `whisper_python` / `transcribe_script` / `punct_model`）未配置或文件不存在时非零退出。Chrome 为可选备用路径，未配置只提示需要 `browser_exec` 备用路径，不影响退出码。它只做配置与文件存在性检查（不代表 GPU / 授权 / 模型已就绪），不联网、不采集、不写表。详见 `docs/CONFIGURATION.md`。

## 5. 离线测试

```bash
python -m unittest discover -s tests -v
```

测试不需要网络、浏览器、飞书或模型：只 mock 飞书 CLI 边界与浏览器启动。本机运行时临时目录落在项目内（`D:` 盘）；非 `D:` 盘环境（例如 CI）回退到平台临时目录。
