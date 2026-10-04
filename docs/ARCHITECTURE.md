# 架构：组件、数据流与状态机

本文件描述单篇视频入库（默认链路）的工程结构。所有路径以仓库相对路径给出；本机绝对路径与访问凭据**只存在于** `config.local.json`，不入库、不写进任何文档与测试。

## 组件

| 组件 | 职责 |
|---|---|
| `scripts/xhs_pipeline.py` | 编排入口（CLI）。子命令 `fetch`（采集 + 查重 + 下载 + 转写 + 标点）、`push`（写入飞书 + 精确回读）、`repair`（疑点局部重转）、`doctor`（本地自检，非零退出、不联网）。读取 `config.local.json`。 |
| `scripts/xhs_collect.mjs` | 通过 CDP 从专用 Chrome 读取小红书页面数据（`window.__INITIAL_STATE__.note.noteDetailMap[笔记ID].note`），输出笔记与媒体地址。 |
| `scripts/douyin_collect.mjs` | 通过 CDP 读取抖音作品详情，映射为与小红书相同形状的笔记对象。 |
| `scripts/punctuate.py` | 本地标点（CT-Transformer ONNX）。只与原文比较非空白、非标点字符；检测到改字就拒绝输出。 |
| `scripts/product_rules.py` | 纯函数：互动数换算（含“评论未显示写 0、其它留空”）、标题来源与备注文案、回读字段校验、`write-state.json` 读写、平台判定与端口探测。 |
| `scripts/xiaohongshu_reach.py` | **非默认**的旧 Markdown 归档链路（图文 / 主页批量 / Mac MLX 视频）。不在本默认链路内。 |
| `tests/` | 离线单元测试，使用标准库；不联网、不访问真实浏览器与飞书。 |
| `assets/readme/*.svg` | 静态手写 SVG（hero、流程图）。纯几何与排版，无脚本、无外链字体、无 `foreignObject`。 |

## 数据流（单篇视频）

```text
链接/分享口令
  → 解析出 URL 与笔记 ID
  → 专用 Chrome（固定端口；不可用时复用配置目录里的 DevToolsActivePort）
  → node 采集器输出 note.json（标题、作者、时间、互动数、标签、封面、媒体流）
  → 查重（按笔记链接过滤既有记录）
      ├─ 命中且非 --force：跳过下载与转写，转入 push 只更新互动数与采集时间
      └─ 未命中：下载封面 → 下载带声音的 mp4 → ffmpeg 抽 16k 单声道音频
                 → Whisper 转写 raw.txt → 本地标点 reviewed.txt
  → push：补齐标签选项 → 新建或更新记录
  → 写 write-state.json（written_unverified）
  → 上传封面附件
  → 精确回读核对（最多 5 次、间隔 2 秒）
  → 通过后清理工作目录
```

要点：

- **查重在写入之前**：查重失败即停止，不盲写。
- **验收以回读为准**：本地文件或命令返回 `ok` 都不算完成，只有目标 `record_id` 的字段回读一致才算。
- **本地标点不改字**：加标点前后做字符级比较，异常输出直接拒绝，不会静默采用。

## 写入状态机

```text
collected           已采集，尚未入表
  → prepared        稿件与封面临时文件就绪
  → written_unverified  记录可能已建，但回读或附件未验证（存在 write-state.json）
  → verified        精确回读通过（终态）
duplicate_updated   命中既有完整记录，仅更新互动数与采集时间
```

- `written_unverified` 是**可恢复**状态：下次运行先查重，确认该 `record_id` 属于本笔记 ID 后，按同一 `record_id` 补写正文与封面，**不会再次新建**。
- 任何失败都保留工作目录与 `record_id`；只有回读通过才删除临时目录。
- 标签选项在飞书侧生效有延迟；写入遇 `800030005 not_found` 时会等待重试，而不是当作失败。

## 配置

所有可变的机器相关值与访问凭据都在 `config.local.json`（由 `config.example.json` 复制，已 gitignore）：

`XHS_BASE_TOKEN`、`XHS_TABLE_ID`、`XHS_LARK_CLI`、`XHS_WHISPER_PYTHON`、`XHS_TRANSCRIBE_SCRIPT`、`XHS_PUNCT_MODEL`、`XHS_SCRATCH_DIR`、`XHS_CHROME_PATH`、`XHS_CHROME_PROFILE`、`XHS_CDP_PORT`。

逐项说明见 [CONFIGURATION.md](./CONFIGURATION.md)。`doctor` 只做本地检查：缺必需项或核心工具路径（未配置/不存在）时以非零退出并提示，Chrome 缺失只降级为 `browser_exec` 备用路径的提醒；不发起任何远程操作，也不等于 GPU / 授权 / 模型已就绪。

## 安全边界

- **不读浏览器凭据**：只用 Chrome 的调试端口读取页面渲染结果，不读取 Profile、Cookie 或密码库，也不结束使用者自己的 Chrome 进程。
- **只发必要数据**：写入飞书的内容来自页面数据与本地成稿；媒体下载只带平台 Referer 头。
- **凭据隔离**：base token、表 ID 等只从 `config.local.json` 读取，仓库内示例文件留空，`.gitignore` 忽略本地配置。
- **离线测试**：`tests/` 不接触网络、浏览器或飞书；CI 同样只跑离线检查。

## 为什么不把整条链路画成"已验收"

默认链路的真实执行路径依赖：专用 Chrome、本地模型、使用者自己的飞书表与授权。这些都不在仓库内，也无法在离线 CI 中复现。因此本项目的验收判据始终是**使用者本机对真实记录的精确回读**，文档与 CI 都不替代它。
