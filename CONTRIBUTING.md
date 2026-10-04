# 贡献指南

感谢愿意改进这个项目。它是一个**本地**工作流 Skill，测试是**离线单元测试**：不联网、不启动浏览器、不访问真实飞书。请保持这条边界。

## 环境

- Windows 11 + Git Bash（主要实测环境）；其它平台未验证，欢迎以问题报告补充。
- `python`（Windows 上 `python3` 常是微软商店占位符，请用 `python`）。
- `node`（采集脚本依赖较新的 Node）。
- 运行测试**不需要**安装 `requirements.txt` 里的 ASR/标点依赖；只有真正跑转写链路才需要。

## 运行测试

```bash
# 标准库 unittest，离线
python -m unittest discover -s tests -v

# 如果本机装了 pytest，也可以
python -m pytest tests -q
```

提交前请再跑一遍这些**离线**静态检查：

```bash
python -m compileall -q scripts tests
node --check scripts/xhs_collect.mjs
node --check scripts/douyin_collect.mjs
```

以上都不会联网、不会调用 `lark-cli`、不会启动 Chrome。

## 不要提交这些

- `config.local.json` 或任何真实配置：base token、table id、笔记 id、record_id。
- 真实逐字稿、作者标题、封面、视频/音频文件、任何媒体 URL。
- 本机绝对路径（个人目录、模型目录等）。
- 凭据、Cookie、浏览器 Profile。

示例文件只放占位符（如 `YOUR_FEISHU_BASE_TOKEN`）。

## 文档与视觉资产

- 本页面的 SVG 在 `assets/readme/`，是**手写静态 SVG**：不要引入 `<script>`、`foreignObject`、外链字体或远程图片。正文保留 Markdown，保证可复制、可搜索。
- 改动 README 或图片引用后，跑一次仓库校验：

  ```bash
  python -m unittest discover -s tests
  ```

  如果要单独校验 README 的本地图片与 SVG 基础，可使用项目中已有的审计方式（见 `tests/`），确保图片都存在、SVG 能被 XML 解析且不含不支持标签。

## 提 PR

1. 一个 PR 只做一件事，说明**动机**与**改动范围**。
2. 行为变化要带测试；纯文档/资产改动请说明为何不需要测试。
3. 不要在 PR 里附真实数据或截图中的个人信息。
4. 不要声称 CI 已通过，除非你确实看到了对应运行结果。

## 许可

来源与开源许可**尚未确认**，见 [docs/PROVENANCE.md](./docs/PROVENANCE.md)。在许可明确之前，请只做本地用途的改动，不要对外重新分发。
