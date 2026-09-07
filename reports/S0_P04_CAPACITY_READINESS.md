# S0｜真实容量前的固定样本准备

状态：**仅元数据准备，未授权编码或模型运行**。T1 数据 CPU 与 E1 模型 CPU 两包仍在实现；后续[原生运行 CPU 接口](../coordination/tasks/P04_SFT_QWEN_RUNTIME_CPU.md)为 PLANNED，等待两包独立审查和 main 验证。

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
