# 第三方来源与许可证

本目录是把「单篇小红书视频 → 飞书」工作流整理成的本地 Skill 项目。以下第三方组件是**运行时依赖**（本目录不随附其源码或模型权重），列出以便署名与合规。项目自身内容不因本文档而被赋予任何公开再许可（见 `docs/PROVENANCE.md`）。

| 项目 | 本包使用方式 | 许可证 | 来源 |
|---|---|---|---|
| lark-cli | 外部 CLI，调用飞书 API | MIT；完整文本见 `LICENSES/LARK-CLI-MIT.txt` | https://github.com/larksuite/cli |
| faster-whisper | pip 依赖（ASR） | MIT | https://github.com/SYSTRAN/faster-whisper |
| sherpa-onnx | pip 依赖（本地标点） | Apache License 2.0 | https://github.com/k2-fsa/sherpa-onnx |
| Node.js | 外部运行时（采集 `.mjs`） | MIT | https://nodejs.org/ |
| FFmpeg | 外部二进制（音视频处理） | LGPL/GPL（按构建） | https://ffmpeg.org/ |

说明：本目录未内置上述组件的源码、模型权重或二进制；pip 依赖由使用者自行安装。法定署名和许可证名称保留原文，它们不代表本项目或本工作流由这些上游项目背书。
