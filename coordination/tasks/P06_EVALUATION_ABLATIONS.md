# P06｜冻结评测与消融

规划状态：P00 为 READY，其余待依赖通过。尚未分发或领取。

| 字段 | 初始值 |
|---|---|
| owner 角色 | E1 |
| 依赖 | P04；M2对照依赖P05 |
| base commit | UNASSIGNED — S0 分发前填实际完整 SHA |
| branch/worktree | UNASSIGNED — 每包独立，不共用 checkout |
| 契约 | toolalign.*.v1，P00 冻结后填写精确版本 |
| 交接 | `coordination/handoffs/P06-r1.md` |

## 目标

冻结正式协议，执行本地任务与清楚命名BFCL子集；统计模型对照、有限重试消融、类别错误与不确定性。

## 允许修改范围

src/toolalign/evaluation、tests/evaluation、reports/benchmarks；不修改模型checkpoint。

除此之外文件默认只读；公共契约、依赖锁和main合并权归S0。路径尚未创建时，先核对P00结构，不能各自发明一套。

## 非目标

不以测试结果反复调prompt；不把子集分数叫BFCL overall；不删掉格式失败的分母。

## 验收

版本/分类/排除清单；成功数/分母；多解oracle反例；配对group bootstrap或说明未做；20类覆盖坏例；单训练seed限制；全部输出hash可追溯。

S0/worker在实际实现前把上述验收转换成可运行命令与预期，完成后附命令/退出码/日志。当前没有声称这些测试已执行。

## 资源

任何模型加载/训练/大批生成都先申请全局GPU锁。默认零外部付费；具体token/内存/时间预算使用P01实测。不要把其他worktree的空闲误认为GPU空闲。

## 阻塞处理

官方分类不可支持则标排除；发现scorer bug提高版本并全比较模型重跑，不只修差模型。

## 交接要求

使用../templates/HANDOFF.md；附关键输入输出、个人应理解的技术点、真实commit、未完成项和独立审查请求。自测通过不自动变成MERGED/VERIFIED。
