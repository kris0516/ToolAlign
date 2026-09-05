# S0-SHARED-01｜公共依赖与来源政策交接

owner：S0；日期：2026-09-06；结论：READY_FOR_REVIEW。

- base：`4cfbe1a5b8d93c20d7b11ec14b31757a574d0903`。
- branch：`work/shared-compat-source-policy`；本交接随最终候选提交，精确 head 由 S0 原生审查消息固定，R1 必须记录该 SHA。
- 任务：`coordination/tasks/S0_SHARED_01.md`；决定：ADR-0011/0012。
- 本包没有修改冻结 schema/validator/Protocol/运行配置或 worker 代码；新增可选依赖与真实来源适配政策。
- 自查：58 项 CPU 测试、lint/冻结/公开扫描、默认和可选环境安装、metadata、跨平台 dry-run 均通过；详见 `reports/S0_SHARED_01.md`。
- R1 重点：默认 CPU 隔离、platform markers/lock/hash、来源许可与可追溯转换；sandbox_only 是项目限制但无执行授权，不能被误读为实际 API 已沙箱化；禁止隐藏未知约束、自动补参数或通过改名绕过去重。
- R1 只编辑自身审查目录/交接，不修实现，不改状态，不执行模型。需要额外原始证据由 S0 指明私有文件，不能把日志中的路径发布。

未完成：独立 R1、候选 CI、合并/main 验证；以及 P01 模型/数学最终验收、P02 适配实现/人工质量门、P03 注册边界实现。后者不因本包通过而视为完成。
