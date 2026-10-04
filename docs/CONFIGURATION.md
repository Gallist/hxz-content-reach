# 配置

本 Skill 的飞书目标和本机工具路径全部来自配置，不写死在代码里。解析优先级（高到低）：

1. 环境变量（`XHS_*`）
2. JSON 配置文件：`$XHS_CONFIG_FILE` 指定的文件；未设置时用项目根目录下的 `config.local.json`（已被 `.gitignore` 忽略）
3. 可移植默认 / PATH 查找（`lark-cli`、`chrome`）

`config.local.json` 从 `config.example.json` 复制；示例里只有占位符（如 `YOUR_FEISHU_BASE_TOKEN`、`YOUR_FEISHU_TABLE_ID`），没有任何真实 base/table/token 或个人路径。**不要把真实配置提交进 Git。**

## 键与对应的环境变量

| 键（配置文件） | 环境变量 | 说明 |
|---|---|---|
| `base_token` | `XHS_BASE_TOKEN` | 飞书多维表格 Base token；缺失时 `fetch` / `push` 会拒绝运行 |
| `table_id` | `XHS_TABLE_ID` | 目标数据表 id；缺失同上 |
| `lark_cli` | `XHS_LARK_CLI` | 飞书 CLI 可执行文件；默认从 PATH 查 `lark-cli` |
| `whisper_python` | `XHS_WHISPER_PYTHON` | ASR venv 的 python；`transcribe.py` / `punctuate.py` 用它跑 |
| `transcribe_script` | `XHS_TRANSCRIBE_SCRIPT` | 转写脚本路径；默认 `.` 下 `scripts/transcribe.py` |
| `whisper_model` | `XHS_WHISPER_MODEL` | Whisper 模型名/路径；默认 `large-v3-turbo` |
| `hf_home` | `XHS_HF_HOME` | HuggingFace 缓存目录 |
| `punct_model` | `XHS_PUNCT_MODEL` | CT-Transformer ONNX；未配置时 `punctuate.py` 明确报错 |
| `scratch_dir` | `XHS_SCRATCH_DIR` | 工作目录根；默认项目下 `.work` |
| `chrome_path` | `XHS_CHROME_PATH` | Chrome 可执行文件；默认从 PATH 查找 |
| `chrome_profile` | `XHS_CHROME_PROFILE` | 专用 Chrome Profile 目录 |
| `cdp_port` | `XHS_CDP_PORT` | 调试端口；默认 `9333` |

## 例子

`config.local.json`：

```json
{
  "base_token": "YOUR_FEISHU_BASE_TOKEN",
  "table_id": "YOUR_FEISHU_TABLE_ID",
  "punct_model": "D:/path/to/punct/model.onnx",
  "scratch_dir": "D:/path/to/work"
}
```

只用环境变量：

```bash
export XHS_BASE_TOKEN=...
export XHS_TABLE_ID=...
export XHS_PUNCT_MODEL=D:/path/to/punct/model.onnx
python "$SKILL_DIR/scripts/xhs_pipeline.py" doctor
```

使用别处的一份 JSON：

```bash
export XHS_CONFIG_FILE=D:/secure/xhs-config.json
```

## 自检

```bash
python "$SKILL_DIR/scripts/xhs_pipeline.py" doctor
```

`doctor` 是离线诊断：列出每个键的值（`base_token` / `table_id` 只显示是否设置及长度，不打印原值）、当前配置文件路径、缺项、核心工具路径与存在的提醒。缺必需项（含 `config.example.json` 原样占位的 `YOUR_*`）或核心工具路径（`lark_cli` / `whisper_python` / `transcribe_script` / `punct_model`）未配置、或配置了但文件不存在时，非零退出。Chrome（`chrome_path` / `chrome_profile`）是可选备用路径：未配置只在 `warnings` 里提示需要 `browser_exec` 备用路径，不导致非零退出。它只检查配置与文件/路径存在性，**不代表 GPU、飞书授权或模型权重完整可用**。它不联网、不采集、不写表，也不启动 Chrome / 不调用 `lark-cli`。

`fetch` 和 `push` 在真正做飞书写入前会调用同一套校验：缺 `base_token` / `table_id` 时给出明确中文提示并停止，不会盲写。导入脚本本身不需要配置，因此离线单测可以在没有任何配置的情况下运行。
