# P03｜可执行工具与语义 oracle

规划状态：P00 为 READY，其余待依赖通过。尚未分发或领取。

| 字段 | 初始值 |
|---|---|
| owner 角色 | E1 |
| 依赖 | P00 |
| base commit | UNASSIGNED — S0 分发前填实际完整 SHA |
| branch/worktree | UNASSIGNED — 每包独立，不共用 checkout |
| 契约 | toolalign.*.v1，P00 冻结后填写精确版本 |
| 交接 | `coordination/handoffs/P03-r1.md` |

## 目标

构建原创本地开发运维工具环境、注册/验证/执行链路、隐藏 oracle 和故障注入；先提供原始模型可用评测入口。

## 允许修改范围

src/toolalign/tools、src/toolalign/evaluation/oracles、tests/tools、允许公开的小 fixtures。

除此之外文件默认只读；公共契约、依赖锁和main合并权归S0。路径尚未创建时，先核对P00结构，不能各自发明一套。

## 非目标

不调用真实写操作、支付或私有 API；不执行模型生成的 Python/shell/SQL；不冒充真实生产流量。

## 验收

至少六类工具任务；错语义但可运行调用判失败；合理多解判通过；无工具/缺参数/超时/未知工具/预算终止；oracle 不出现在输入；原始和修复输出分离。

S0/worker在实际实现前把上述验收转换成可运行命令与预期，完成后附命令/退出码/日志。当前没有声称这些测试已执行。

## 资源

任何模型加载/训练/大批生成都先申请全局GPU锁。默认零外部付费；具体token/内存/时间预算使用P01实测。不要把其他worktree的空闲误认为GPU空闲。

## 阻塞处理

无法建立可靠 oracle 的任务标 unknown/排除并报告，不用 LLM 自评补齐。

## 交接要求

使用../templates/HANDOFF.md；附关键输入输出、个人应理解的技术点、真实commit、未完成项和独立审查请求。自测通过不自动变成MERGED/VERIFIED。
