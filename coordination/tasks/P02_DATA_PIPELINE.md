# P02｜数据规范化、许可与分组隔离

规划状态：P00 为 READY，其余待依赖通过。尚未分发或领取。

| 字段 | 初始值 |
|---|---|
| owner 角色 | D1 |
| 依赖 | P00 |
| base commit | UNASSIGNED — S0 分发前填实际完整 SHA |
| branch/worktree | UNASSIGNED — 每包独立，不共用 checkout |
| 契约 | toolalign.*.v1，P00 冻结后填写精确版本 |
| 交接 | `coordination/handoffs/P02-r1.md` |

## 目标

实现 ToolACE 为主的可复现导入与审计；xLAM 可选；分组切分、token 长度和人工抽检报告。

## 允许修改范围

src/toolalign/data、tests/data、数据 manifest 与审计报告；不改 training/evaluation 公共接口。

除此之外文件默认只读；公共契约、依赖锁和main合并权归S0。路径尚未创建时，先核对P00结构，不能各自发明一套。

## 非目标

不提交全量原始数据，不自动接受 gated 条款，不训练测试集，不用模型补造缺失真值。

## 验收

同输入重建 split 一致；group 无交叉；改写留原组；长样本处理明确；恶意 schema/数据解析拒绝；许可与排除计数齐全；kris 抽检。

S0/worker在实际实现前把上述验收转换成可运行命令与预期，完成后附命令/退出码/日志。当前没有声称这些测试已执行。

## 资源

任何模型加载/训练/大批生成都先申请全局GPU锁。默认零外部付费；具体token/内存/时间预算使用P01实测。不要把其他worktree的空闲误认为GPU空闲。

## 阻塞处理

数据访问受限仅使用可用来源；长度过长先缩工具集合/分桶并报告，不静默截断。

## 交接要求

使用../templates/HANDOFF.md；附关键输入输出、个人应理解的技术点、真实commit、未完成项和独立审查请求。自测通过不自动变成MERGED/VERIFIED。
