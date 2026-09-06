# P04｜原始模型与 SFT 实验

状态：BLOCKED；尚未分发或领取正式训练。P00、P01受限G1、P03 CPU、新格式及截止时间修订已VERIFIED。训练绑定已随[PR9](https://github.com/kris0516/ToolAlign/pull/9)合并42eaa50并完成最终双Python CI与main919CPU/2 HF-only skipped、现存三归档及49份安装包载荷绑定，CPU技术范围VERIFIED；原R1 PASS40252f8保持。见[主干证据](../../reports/S0_P02_TRAINING_BINDING_MAIN_VERIFICATION.md)。仍待P02真实语义人审、代表/最长/非ASCII实际页面观察和token/mask人工核对；实际trainer/collator、尾批、checkpoint与0.6B容量验证尚未完成。S0准备不构成P04训练授权。

| 字段 | 初始值 |
|---|---|
| owner 角色 | T1 |
| 依赖 | P01,P02,P03 |
| base commit | UNASSIGNED — S0 分发前填实际完整 SHA |
| branch/worktree | UNASSIGNED — 每包独立，不共用 checkout |
| 契约 | toolalign.*.v1，P00 冻结后填写精确版本 |
| 交接 | `coordination/handoffs/P04-r1.md` |

## 目标

固定1.7B原始模型基线，完成 completion-only SFT 和验证集 checkpoint 选择；0.6B 先作为 smoke。

## 允许修改范围

src/toolalign/training/sft、tests/training、reports/experiments；训练 config 由 S0 合并。

除此之外文件默认只读；公共契约、依赖锁和main合并权归S0。路径尚未创建时，先核对P00结构，不能各自发明一套。

## 非目标

不看最终测试调参，不同时换模型容量和算法，不把 adapter 文件出现当训练完成。

## 验收

10条token/mask人工核对；少量样本过拟合；正式run manifest；训练参数变化范围；保存重载；原始/SFT同生成配置；真实资源和失败日志。

S0/worker在实际实现前把上述验收转换成可运行命令与预期，完成后附命令/退出码/日志。当前没有声称这些测试已执行。

## 资源

任何模型加载/训练/大批生成都先申请全局GPU锁。默认零外部付费；具体token/内存/时间预算使用P01实测。不要把其他worktree的空闲误认为GPU空闲。

## 阻塞处理

超预算减少正式数据或对照数量，保留 baseline、split 和完整证据；停止无收益扫参。

## 交接要求

使用../templates/HANDOFF.md；附关键输入输出、个人应理解的技术点、真实commit、未完成项和独立审查请求。自测通过不自动变成MERGED/VERIFIED。

## S0只读准备中的必要验证点

2026-09-06，见[输入与上游控制流记录](../../reports/S0_P04_READINESS.md)。固定MLX-LM版本在非完整累积尾批不会补更新，末次内置validation又发生在最后训练微步前。P04实现前必须登记尾批缩放/真实更新与数据覆盖规则，以及validation到实际checkpoint参数hash的绑定；不能静默丢样本或把前一次状态的分数当成最终权重分数。正式方案、运行预算与精确配置仍待S0后续授权，不提前启动任务。

新格式的固定train/validation统计已经改变：在总长≤2048且C含EOS≤256的统计交集中分别有6013/217条；若未来选择该规则，完整单遍train为751个累积8更新加5个尾微步，不能继续使用旧格式7404条的计数。1024档只有985条train，不能写成已具备1k–2k不重复样本的单遍smoke。正式训练规则、0.6B长度前置验证、剩余样本排除/分桶、训练选集manifest及实际预算须另行登记；当前未选择样本或增加模型运行。所用数字保留原表示测量的代码、环境与时间；新格式已获R1 PASS但主干仍待验证，这些数字不是模型性能。


P02的[训练绑定CPU准备](P02_TRAINING_BINDING.md)已READY未派发。其13例token/mask材料为10条实际已选train与3条单列原创非调用Action，后者不加入训练；现有目标全为tool_calls。未来P04须把实际trainer/collator行为与已审材料连接，再完成真实人工、尾批和checkpoint验收。本段不领取或授权正式P04。


上述P02训练绑定CPU准备已按完整5d2c6b6原生派发D1并核验ACTIVE；该实际派发不构成正式P04领取/模型训练授权，待候选和人工门槛。


ADR-0020另行准备[P04-SFT-CPU](P04_SFT_CPU_PREPARATION.md)：先在已验证42eaa50完成数据/collator和极小原创CPU数值衔接，当前READY未派发。该子包依赖技术基线，不代签G-DATA/实际页面/token-mask人工，不领取本包正式训练；真实模型、LoRA配置、运行预算与容量门槛仍待后续完整授权。


14:53 UTC，P04-SFT-CPU已按完整e42536d原生派发T1并核验新轮ACTIVE；此实际派发仅覆盖该CPU子包，不构成本包正式训练领取。新分支/输入intake尚待确认，原人工和真实模型门槛保持。
