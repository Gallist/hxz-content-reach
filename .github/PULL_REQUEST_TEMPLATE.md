<!--
请在提交前确认以下内容。这个项目是一个尚未发布的导出副本，请如实描述你验证过的范围。
-->

## 这个 PR 做了什么

<!-- 一到两句话说清动机与改动范围 -->

## 改动类型

- [ ] Bug 修复
- [ ] 新能力
- [ ] 文档
- [ ] 测试 / CI
- [ ] 视觉资产（`assets/readme/*.svg`）
- [ ] 重构（不改变行为）

## 我验证了什么

- [ ] `python -m compileall -q scripts tests`
- [ ] `python -m unittest discover -s tests -v`
- [ ] `node --check scripts/xhs_collect.mjs` 与 `node --check scripts/douyin_collect.mjs`（如改了采集脚本）
- [ ] 如改了 README / 图片引用，已确认本地图片存在、SVG 能解析且不含 `<script>` / `foreignObject` / 外链字体

<!-- 请粘贴你实际看到的结果，不要写“应该通过”。 -->

## 边界与诚实性检查

- [ ] 我没有提交真实凭据、table id、笔记 id、record_id、逐字稿、媒体 URL 或本机绝对路径
- [ ] 我没有新增联网的测试，也没有让测试依赖真实浏览器或飞书
- [ ] 如果这次改动影响实时链路，我说明了自己**没有**验证的部分
- [ ] 我没有声称远程 CI 已通过，除非我确实看到了该次运行结果

## 备注

<!-- 关联 issue、未解决的点、需要 reviewer 特别看的文件 -->
