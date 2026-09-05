# P01｜Mac 校准与 SFT/DPO 兼容性

规划状态：P00 为 READY，其余待依赖通过。尚未分发或领取。

| 字段 | 初始值 |
|---|---|
| owner 角色 | T1 |
| 依赖 | P00 |
| base commit | UNASSIGNED — S0 分发前填实际完整 SHA |
| branch/worktree | UNASSIGNED — 每包独立，不共用 checkout |
| 契约 | toolalign.*.v1，P00 冻结后填写精确版本 |
| 交接 | `coordination/handoffs/P01-r1.md` |

## 目标

核实真实硬件/环境；0.6B 加载和微训练；1.7B 真实长度校准；验证候选 DPO backend 的数学/reference/adapter 兼容。

## 允许修改范围

src/toolalign/training/compatibility、训练测试、reports/hardware 与兼容摘要；依赖变更交 S0。

除此之外文件默认只读；公共契约、依赖锁和main合并权归S0。路径尚未创建时，先核对P00结构，不能各自发明一套。

## 非目标

不运行全数据集，不以第三方 benchmark 替代本机测量，不抬高系统内存限制。

## 验收

加载/保存/重载一致；CE/DPO PyTorch CPU 对照；reference 冻结和初始 ln2；跨库前向；100 微步或实际样本说明；共享 GPU 锁竞争测试。

S0/worker在实际实现前把上述验收转换成可运行命令与预期，完成后附命令/退出码/日志。当前没有声称这些测试已执行。

## 资源

任何模型加载/训练/大批生成都先申请全局GPU锁。默认零外部付费；具体token/内存/时间预算使用P01实测。不要把其他worktree的空闲误认为GPU空闲。

## 阻塞处理

D2 前确定一条正式 DPO 路线；只切一次备选；失败交精确 error/reproducer，core 可以仅先推进 SFT。

## 交接要求

使用../templates/HANDOFF.md；附关键输入输出、个人应理解的技术点、真实commit、未完成项和独立审查请求。自测通过不自动变成MERGED/VERIFIED。
