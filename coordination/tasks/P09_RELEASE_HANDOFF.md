# P09｜发布、回滚与负责人交接

规划状态：P00 为 READY，其余待依赖通过。尚未分发或领取。

| 字段 | 初始值 |
|---|---|
| owner 角色 | S0 |
| 依赖 | 对应release级别的P08 PASS |
| base commit | UNASSIGNED — S0 分发前填实际完整 SHA |
| branch/worktree | UNASSIGNED — 每包独立，不共用 checkout |
| 契约 | toolalign.*.v1，P00 冻结后填写精确版本 |
| 交接 | `coordination/handoffs/P09-r1.md` |

## 目标

按真实完成级别发布、整理复现入口/模型卡/局限/许可和实测表；完成kris项目答辩检查。

## 允许修改范围

README、CHANGELOG、reports/releases、公开制品manifest与coordination状态。

除此之外文件默认只读；公共契约、依赖锁和main合并权归S0。路径尚未创建时，先核对P00结构，不能各自发明一套。

## 非目标

不自动上传权重/数据、不申请付费资源、不声明完整BFCL/多卡/生产部署未验证成果。

## 验收

干净环境复现；GitHub实际commit/public读回；无秘密/大数据；结果可追溯；adapter发布需单独授权；上一稳定制品可恢复。

S0/worker在实际实现前把上述验收转换成可运行命令与预期，完成后附命令/退出码/日志。当前没有声称这些测试已执行。

## 资源

任何模型加载/训练/大批生成都先申请全局GPU锁。默认零外部付费；具体token/内存/时间预算使用P01实测。不要把其他worktree的空闲误认为GPU空闲。

## 阻塞处理

只core通过就发v0.1.0-core并列DPO未完成；不要为了标签齐全造完成项。

## 交接要求

使用../templates/HANDOFF.md；附关键输入输出、个人应理解的技术点、真实commit、未完成项和独立审查请求。自测通过不自动变成MERGED/VERIFIED。
