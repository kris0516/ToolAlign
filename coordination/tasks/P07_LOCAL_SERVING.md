# P07｜本地服务与 prefix-cache 对照

规划状态：P00 为 READY，其余待依赖通过。尚未分发或领取。

| 字段 | 初始值 |
|---|---|
| owner 角色 | I1 |
| 依赖 | P01,P03,P04；具体模型由S0指定 |
| base commit | UNASSIGNED — S0 分发前填实际完整 SHA |
| branch/worktree | UNASSIGNED — 每包独立，不共用 checkout |
| 契约 | toolalign.*.v1，P00 冻结后填写精确版本 |
| 交接 | `coordination/handoffs/P07-r1.md` |

## 目标

实现loopback原生MLX worker、有限队列、鉴权/预算/取消、模型身份与cache；一次固定配置cold/warm对照。

## 允许修改范围

src/toolalign/inference、src/toolalign/service、tests/service、reports/performance。

除此之外文件默认只读；公共契约、依赖锁和main合并权归S0。路径尚未创建时，先核对P00结构，不能各自发明一套。

## 非目标

不公开端口，不引入生产多租户、Kubernetes或复杂前端，不让Linux Docker假装获得Metal GPU。

## 验收

health/ready分离；模型更新cache失效；prefix/tenant隔离；重复key不同payload拒绝；取消/超时；训练互斥；TTFT/队列/端到端分开；实测请求数。

S0/worker在实际实现前把上述验收转换成可运行命令与预期，完成后附命令/退出码/日志。当前没有声称这些测试已执行。

## 资源

任何模型加载/训练/大批生成都先申请全局GPU锁。默认零外部付费；具体token/内存/时间预算使用P01实测。不要把其他worktree的空闲误认为GPU空闲。

## 阻塞处理

资源冲突先停serving让训练完成；高级KV量化/投机解码后移，不以样本不足P95宣称SLO。

## 交接要求

使用../templates/HANDOFF.md；附关键输入输出、个人应理解的技术点、真实commit、未完成项和独立审查请求。自测通过不自动变成MERGED/VERIFIED。
