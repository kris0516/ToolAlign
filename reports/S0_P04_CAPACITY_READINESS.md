# S0｜真实容量前的固定样本准备

状态：**仅元数据准备，未授权编码或模型运行**。T1 数据 CPU 修订1769046已完整接收、独立复审READY；E1模型01ee的R1独立审查正在进行；后续[原生运行 CPU 接口](../coordination/tasks/P04_SFT_QWEN_RUNTIME_CPU.md)为 PLANNED，等待两包独立审查和 main 验证。

2026-09-07 18:57:34 UTC，S0按已接收的[原运行方案](experiments/P04_SFT_RUNTIME_PROPOSAL.md)冻结0.6B容量候选：15个train、8个validation。只用已验收v3 smoke的长度/rank元数据，先选1536 bucket内总长最大、C最长、C最短的train，按原rank打破并列并补足15例；validation选总长最大、C最长并按rank补足8例。没有查看新模型输出；没有读取test/ood/BFCL内容、重新分词或复制原样本。

| 已有审计元数据 | 15个train | 8个validation |
|---|---:|---:|
| 原smoke rank | 1–12、21、53、807 | 1–6、64、150 |
| sequence token总数 | 18,524 | 9,335 |
| 逻辑padding token总数 | 20,992 | 10,752 |
| 监督token总数 | 1,536 | 1,006 |
| 1536 bucket例数 | 11 | 5 |
| 最大实际sequence长度 | 1,536 | 1,519 |

这些数字来自既有逐例审计，尚未用新数组或真实trainer复核。原始行hash、各代rank、Example/source/group身份与精确来源均在私有固定cohort中，SHA `a6e09dbff4050f259ac5219efc0b67fb3a89a601c5d56dd2125b7bcb9dfe9f6d`；S0准备证明 `04bb6a6ea1e6ef760c71393788df3c407a26d1f9c5d7789c287d55391a1fdb2a`。原数据候选5825d789、R1 dbd11d0、Q1 7941f1f与G-DATA批准1edb1e88保持；模型metadata b8a5e48b仅供未来绑定。

15例8+7及前8例重复8遍的提案共79微步/10更新，按该固定cohort对应111,104逻辑padding token、8,320监督token。实际更新0；23例新编码、真实1536容量、零LoRA对照、CE下降、保存/重载和内存/时延全部NOT_RUN。完整smoke/formal不继承容量adapter；其预算与真实运行授权分别冻结。

2026-09-07 21:41:04 UTC，S0只用上述原cohort元数据，冻结[容量诊断计划](../coordination/plans/P04_QWEN_CAPACITY_DIAGNOSTICS.v1.json) `a25ddc2e3a3df72cee145fb41778e837c4907062828ac421c5eb6242f487486c`；准备证明 `c69dee81cb40a54c8e4e17ab35e2bb9c895c088ff24dff9b8b8535e5c539472f`。未读取新原文或模型输出，23个唯一例及原cohort SHA不变。

| 未来诊断状态 | 固定前向例次 |
|---|---:|
| raw step0 validation | 8 |
| raw及零LoRA的同例padded/unpadded两对照 | 4 |
| step2的原前8个train及8个validation | 16 |
| step10的同8个train及8个validation | 16 |
| 顺序重载step10后同8个train及8个validation | 16 |
| 合计 | 60 |

padding对照用原cohort内smoke rank3（实际1510、bucket1536），确有26个右padding位；1536总长的原例仍保留在训练容量15例中。诊断去padding只用于同例因果等价比较，不改变原训练数组或截断有效token。诊断逻辑token82,892，加原训练111,104，共193,996，低于提议总上限262,144；监督token分别7,236/8,320。原64例次上限中的未列4次不成为自由重试额度，生成保持0。所有这些是元数据算术，实际前向/更新仍0。

判定提前固定：同表示零LoRA CE绝对差≤1e-5；BF16 padded/unpadded CE绝对差≤0.02；独立累积与native结果差≤1e-5×max(1,abs(独立CE))；同例重载CE差≤1e-5且A/B/冻结底座原字节一致。过拟合同前8个train的总CE/总监督token须满足CE10≤0.90×CE2或CE10≤0.1。另需初始B全零、至少一个声明A/B变化、底座不变、实际step2/10及完整终态。每例一次前向的未归约loss同时供native返回和独立分母核验，不重复完整validation来获得第二个总数。

本计划是不可执行的前置记录，is_run_authorization/training_authorized/optimization_authorized均false；没有框架/模型/GPU/编码或运行启动额度。原900秒等容量预算仍是待最终CPU代码/实际数组绑定后单独授权的上限提议。CPU运行接口仍PLANNED；其原文已明确保留native compile并固定grad_checkpoint=False，与已接收方案一致。
