# P05｜执行反馈偏好与 DPO

规划状态：P00 为 READY，其余待依赖通过。尚未分发或领取。

| 字段 | 初始值 |
|---|---|
| owner 角色 | T1（训练）；D1（数据子包由 S0 独立分发） |
| 依赖 | P04；P03 oracle 已验收 |
| base commit | UNASSIGNED — S0 分发前填实际完整 SHA |
| branch/worktree | UNASSIGNED — 每包独立，不共用 checkout |
| 契约 | toolalign.*.v1，P00 冻结后填写精确版本 |
| 交接 | `coordination/handoffs/P05-r1.md` |

## 目标

从 train-only 的冻结 SFT 生成候选，形成有语义证据的有效偏好对；以同 SFT 作 reference 运行 DPO。

## 允许修改范围

T1 改 training/dpo 与训练测试；D1 改 data/preferences 与审计，两个独立任务授权不重叠。

除此之外文件默认只读；公共契约、依赖锁和main合并权归S0。路径尚未创建时，先核对P00结构，不能各自发明一套。

## 非目标

不把BFCL/最终测试用于挖负例，不以错格式为全部偏好，不把停adapter当SFT reference。

## 验收

多解tie剔除；独立Q1委托AI分层审查（ADR-0023，保留原内容标准与实际AI身份）；reference logprob缓存身份；ln2/梯度/mask/reload测试；正式paired data/run manifests；SFT对照完全一致。

S0/worker在实际实现前把上述验收转换成可运行命令与预期，完成后附命令/退出码/日志。当前没有声称这些测试已执行。

## 资源

任何模型加载/训练/大批生成都先申请全局GPU锁。默认零外部付费；具体token/内存/时间预算使用P01实测。不要把其他worktree的空闲误认为GPU空闲。

## 阻塞处理

有效对不足先报告；DPO后端错误则不产正式算法结论；缩到0.6B时分表写清，不冒充1.7B。

## 交接要求

使用../templates/HANDOFF.md；附关键输入输出、个人应理解的技术点、真实commit、未完成项和独立审查请求。自测通过不自动变成MERGED/VERIFIED。
