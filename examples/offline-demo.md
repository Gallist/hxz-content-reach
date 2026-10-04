# 离线演示

本示例展示浏览器备用路径（`fetch --note-json`）输入文件的结构，以及如何在不启动 Chrome、不写飞书的情况下做离线自检。所有数据都是合成的，`note_id` 为占位的 24 位十六进制。

## 1. 诊断（离线）

```bash
python "$SKILL_DIR/scripts/xhs_pipeline.py" doctor
```

未配置 base/table（或仍是示例占位 `YOUR_*`）时会列出缺项并返回非零；核心工具路径（`lark_cli` / `whisper_python` / `transcribe_script` / `punct_model`）未配置或不存在时同样返回非零；只有 base/table 与核心工具都就绪才返回 0。Chrome 是可选备用路径，未配置只在提醒里提示需要 `browser_exec` 备用路径，不影响退出码。doctor 只检查配置与文件存在性，不代表 GPU / 授权 / 模型已就绪。

## 2. `--note-json` 输入结构

`examples/page-source.example.json` 是 `fetch --note-json` 期望的页面数据形态：包含 `href`、`note_id`、`title`、`desc`、`type`、`author`、`time`、`interact`、`tags`、`images`、`streams`。它只承载笔记内容与媒体地址，不含任何会话凭据。

## 3. 跑测试（不联网）

```bash
python -m unittest discover -s tests -v
```

测试只 mock 飞书 CLI 边界和浏览器启动，不会真的采集、写入或调用模型。
