# 产品契约、字段映射与验收

本文是「单篇小红书视频入库」的产品契约，对应 SKILL.md 的默认流程。它不是常驻服务，也不是独立网页/插件，而是由 `/hxz-content-reach` 触发的 Skill 工作流。运行边界见 `docs/INSTALL.md`；配置见 `docs/CONFIGURATION.md`。

> 目标表（Base / 表）不写死在本文件：`base_token` / `table_id` 只存在于本地配置（`XHS_BASE_TOKEN`、`XHS_TABLE_ID` 或 `config.local.json`）。

## 1. 用户输入示例

```text
/hxz-content-reach <授权视频链接>
```

- 链接 + 指定本 Skill（或明确说“采集入库”）本身就是本次采集入库授权：直接跑完整流程，不二次询问“要不要录入”。
- 单独一条链接、没有指定 Skill、也没有表达采集入库意图时：先询问，不擅自下载或写入。
- 用户明确要求“先验稿 / 只看看 / 别入库”时：停在其指定阶段，不自动写入。

## 2. 字段映射

| 字段 | 来源 |
|---|---|
| 标题 | 原作者标题 → 封面大字 → 正文首句（都取不到才报告缺失，不拟题） |
| 封面 | `imageList[0].urlDefault`，上传为附件 |
| 类型 | 单选：视频 / 图文 |
| 点赞 / 收藏 / 评论 / 分享 | `interactInfo.likedCount / collectedCount / commentCount / shareCount` |
| 逐字稿 | 本地 `reviewed.txt`（Whisper 转写 + 标点模型） |
| 标签 | 笔记自带 `note.tagList[].name`（多选） |
| 作者 | `user.nickname` |
| 发布日期 | `note.time`（毫秒）转北京时间 `YYYY-MM-DD` |
| 笔记链接 | 含 `xsec_token` 的页面链接 |
| 采集时间 | 本次采集时间 |
| 备注 | 来源限制 + 标题来源的自动说明 |

正常读取笔记页面后，评论数未显示时写 0（用户确认的规则）；其他缺失互动数字**留空**，不填 0。页面读取失败不能据此写 0，仍必须停止采集并报告失败。数字缩写按页面显示精度换算（`1.2万`→12000），不当作隐藏的精确值；`10万+` 是下限值。

## 3. 转写与标点边界（不是全文纠错）

- 默认：本地 Whisper 转写 + CT-Transformer 标点，标点步骤只加标点、不纠错词。它不等于全文纠错，保留原转写错词是用户接受的默认权衡。
- 转写脚本默认离线：`transcribe.py` 的两处模型构造都传 `local_files_only=True`，缺本地模型就直接报错退出，不会隐式下载权重（CUDA 与 CPU 回退一致）；`XHS_HF_HOME` 优先于既有的 `HF_HOME`。
- 该默认链路不调用云端全文校对，也不新增该步骤的 API 费用。
- 这不等于本机不花钱——GPU、电力和时间仍要花；不要对外说“本机近似免费”或“跑一次不要钱”。
- 与 AI 校对稿的差异比例不等于真实错字率。没有人工听音真值，不把样本差异说成准确率，也不保证其他视频效果一致。

## 4. 标准路径与浏览器备用路径

标准路径（先跑这个）：

```bash
python "$SKILL_DIR/scripts/xhs_pipeline.py" doctor
python "$SKILL_DIR/scripts/xhs_pipeline.py" fetch "<用户链接或分享口令>"
# 查重命中会跳过下载转写并返回既有 workdir；查重失败直接停止，不盲写
python "$SKILL_DIR/scripts/xhs_pipeline.py" push "<fetch返回的workdir>"
```

浏览器备用路径（固定端口专用 Chrome 未启动或不可用时）：

1. `browser_exec(local=True)` 的 `new_tab` 打开笔记链接。
2. 用 `js(...)` 执行 `xhs_collect.mjs` 里已验证的 EXTRACT 表达式，读 `window.__INITIAL_STATE__.note.noteDetailMap[笔记ID].note`。
3. 把页面数据写到任务临时目录的 `page-source.json`（只含笔记内容和媒体地址，不含会话凭据）。
4. 用同一条执行器续跑：`fetch "<链接>" --note-json <page-source.json 绝对路径>`。

边界：不读浏览器 Profile / Cookie / 密码库，不 kill 使用者自己的 Chrome，不按进程名批量 taskkill。备用路径通过浏览器工具，不保证绝对不抢焦点/完全隐藏；做不到就回报具体限制，不把“后台”写成已验证的硬承诺。

账号/授权过期：只有用户本人完成登录。模型不在聊天里接收密码或验证码。

## 5. 可重入策略

写入状态：`collected`（已采集未入表）→ `prepared`（稿与封面临时文件就绪）→ `written_unverified`（记录可能已建，但回读或附件未验证）→ `verified`（精确回读通过）；重复命中既有完整记录为 `duplicate_updated`。

- 重复：同一笔记再次采集，只更新本次可见互动数字和采集时间，不重复新建、不重转写。
- 未验收续跑：`write-state.json` 记录刚创建的 `record_id`。若进程在封面/回读前中断，下次先查重确认该 record_id 属于本笔记 ID，再按同一 record_id 补写和补附件，不再次 `create`。
- 查重失败：停止写入，不绕过查重新建。
- 清理：仅在精确 record_id 回读通过后才删除工作目录；失败保留现场和 record_id，不先删文件。回读失败也保留 state 文件。
- 并发：同一笔记只顺序处理、同一 GPU 顺序转写；不并行写同一篇。

## 6. 计时范围

页面采集、下载/转写/标点、飞书写入与回读分别计时。整条链路总耗时取开始到结束的真实墙钟时间，不把并行步骤耗时简单相加。

一次历史真实样本：音频 601 秒，下载 + 转写 + 标点共 67.47 秒（标点步骤含模型加载约 1.13 秒），本地成稿 23 段。这只是当时单次样本，**不是未来整条链路的固定耗时**；浏览器排障与飞书写入回读不计入这 67.47 秒。不对外承诺固定时长，也不保证在其他机器或视频上复现。

## 7. 验收与恢复命令

验收成功的判据是飞书里的真实记录，而不是本地文件或 CLI 返回 `ok`。

```bash
# 1) 复用真实页面 JSON 命中既有记录，不重下载/重转写（示例）
python "$SKILL_DIR/scripts/xhs_pipeline.py" fetch "https://xhslink.cn/o/<分享口令>" --note-json "<page-source.json 绝对路径>"

# 2) 对返回的精确 workdir 执行 push（既有记录应只更新互动数据）

# 3) 精确回读目标记录
lark-cli base +record-get \
  --base-token <XHS_BASE_TOKEN> --table-id <XHS_TABLE_ID> \
  --record-id <record_id> \
  --field-id 标题 --field-id 封面 --field-id 逐字稿 --field-id 作者 \
  --field-id 点赞 --field-id 收藏 --field-id 评论 --field-id 分享 --field-id 备注 \
  --format ndjson --output verify.ndjson --overwrite --as user
```

期望：`records_count=1`、`has_more=false`；正文与本地 `.strip()` 后的逐字稿一致，封面非空，评论为 0（若页面未显示）。

## 8. 排障细节

- 笔记数据路径：`window.__INITIAL_STATE__.note.noteDetailMap[笔记ID].note`（`title`、`user.nickname`、`time`、`type`、`desc`、`interactInfo.*`、`imageList[].urlDefault`）。下载原图/媒体带 `Referer: https://www.xiaohongshu.com/`。
- 必须有窗口 Chrome：无头 UA 带 `HeadlessChrome`，小红书会跳 `website-login/error?error_code=300012`（IP 风险）。看到先查 UA，别当网络问题。
- 视频转写（Windows）：从媒体流带 Referer 下 mp4 → `ffmpeg -vn -ac 1 -ar 16000 audio.wav` → 用配置的 ASR venv 跑 `transcribe.py audio.wav raw.txt`（faster-whisper）。venv 的 PyAV 与 faster-whisper 不兼容，`transcribe.py` 已改为用 ffmpeg 解码后直接喂 numpy，别改回传文件路径。
- 飞书写入坑：多选写不存在的选项报 `800030005 not_found`，新标签先 `+field-get` 取 options、追加后 `+field-update --yes` 回写再写记录；`+record-upload-attachment --file` 只接受工作目录相对路径（脚本在该目录内执行）；长 JSON 用 `--json @文件名`（同为相对路径）。新标签写后几秒才生效，遇 `800030005` 会自动等待重试。
- 成功后脚本自动删整个临时目录；不要 `cd` 进工作目录，否则终端进程占着它删不掉。

## 9. 未在本次导出验证的部分

- 本导出**没有**做新一轮真机视频验收：没有重新采集真实链接、没有重新跑模型计时、没有重新写飞书。上面 67.47 秒是历史样本。
- `doctor` 只做配置与文件/路径存在性检查：缺必需项（含未替换的示例占位）或核心工具路径时非零退出，但不代表 GPU、飞书授权或模型权重完整可用；未在缺模型机器上专门复测转写的离线报错路径。
- 抖音采集代码（`douyin_collect.mjs` / `douyin_note`）随同一管线保留并有离线单测，但本次导出未对抖音做真机复测。
- 未验证 Linux/macOS；本导出的运行边界是 Windows 11。
