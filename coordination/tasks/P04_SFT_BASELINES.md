# P04｜原始模型与 SFT 实验

最新依赖（2026-09-07，ADR-0022）：本批P02语义/token-mask材料已由kris委托AI审阅，结果进入质量整改；不再等待本人抄填。P04仍BLOCKED于质量修订、新绑定/独立复核及真实模型容量/正式运行授权。浏览器实显0页/NOT_RUN保留，既有拒绝不绕过；页面体验待办不阻塞本轮CPU数据整改。旧时间线中的“待人审”保持其原观察时间，不覆盖该最新委托。

状态：BLOCKED；尚未分发或领取正式训练。P00/P01受限G1/P03 CPU、共用格式、训练绑定与CPU准备已VERIFIED；固定原创native toy亦经R1 PASS67976fd、PR11合并b2247d8及最终CI/main验证，见[数值子包主干证据](../../reports/S0_P04_SFT_NATIVE_TOY_MAIN_VERIFICATION.md)。该证据覆盖13原创rank/64参数的8+5尾批、evaluate及checkpoint；本批语义/token-mask审阅现按ADR-0022采用kris委托AI方式，仍待质量修订/新绑定及独立复核、真实0.6B容量和正式1.7B baseline/SFT。页面体验待办单列为NOT_RUN。training_authorized=false，S0准备及toy验收不构成本包模型训练许可。

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

10条token/mask核对（本批采用ADR-0022中kris明确委托的AI方式，实际trainer对应仍须验证）；少量样本过拟合；正式run manifest；训练参数变化范围；保存重载；原始/SFT同生成配置；真实资源和失败日志。

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


ADR-0021另准备[P04-SFT-NATIVE-TOY](P04_SFT_NATIVE_TOY.md)，基线50867c0，仅固定13原创例/64参数的MLX GPU原生接口与Torch CPU参考数值验证，READY尚未派发。该子包验证尾周期/evaluate/checkpoint；不会读取真实训练样本作优化，不替代本包的人工、容量、baseline和SFT验收。


P04-SFT-NATIVE-TOY已按完整de86568原生派发T1并核验新轮ACTIVE；该实际派发仍仅为固定原创数值子包，原生结果/独立审查和本包正式训练门槛保持待完成。

P04-SFT-NATIVE-TOY现有S0中间证据：S0已核对534445b的两次原GPU运行：13例完整数值、8+5实际更新/两个checkpoint及原单段丢尾反例通过；fae3d60监督器终态缺陷的CPU定点回归通过。完整候选/安装版独立核验、R1、最终CI/main仍待完成；人工与正式P04门槛保持。见[原数值与终态修复](../../reports/S0_P04_SFT_NATIVE_TOY_INTERMEDIATE.md)。该有限原创子包仍不构成本包真实模型baseline/SFT验收。

P04-SFT-NATIVE-TOY完整f7326d1已交付，T1原生空闲，S0完整字节/命令/数值/归档交接核验通过；[R1精确范围](P04_SFT_NATIVE_TOY_REVIEW.md)按完整482f899实际派发并确认新轮ACTIVE，PR11保持Draft。见[完整交接](../../reports/S0_P04_SFT_NATIVE_TOY_HANDOFF.md)。原生toy独立验收及本包实际页面、人审、0.6B容量、1.7B baseline/SFT仍未完成。

原生toy独立部分现ACCEPTED：原R1 67976fd对f7326d1 PASS，T1/R1空闲；S0普通集成a1c467a通过1084CPU/2跳过、新三归档及默认安装/native守卫。见[集成证据](../../reports/S0_P04_SFT_NATIVE_TOY_INTEGRATION.md)。实际8+5更新/evaluate/checkpoint仅覆盖固定原创64参数问题；最终CI/main待完成，本包真实0.6B容量、1.7B baseline/SFT、实际页面和两项人工仍未完成。

21:35 UTC：原生固定toy已完成最终CI/main并VERIFIED，原CPU支持负结果保持。本包真实模型训练及人工依赖继续BLOCKED；本段更新依赖证据，不领取正式P04。
