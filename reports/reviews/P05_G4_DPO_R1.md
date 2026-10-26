# R1｜G4 原生 DPO CPU 技术审查

2026-10-26。**REQUEST_CHANGES**；P0=0、P1=0、P2=1。原生 SUM 损失、mask、冻结 reference 和 CPU 完整恢复获得支持；终态 `summary.json` 未计入完整输出预算，已复现超限仍返回 PASS。E1 修正这一项后可定点复审。

候选为 `982cc1917d23b4004dbf9f683c685515eb390ea7`，审核授权为 `0b470325f0aff277285026f2d6c2e691ee7dd975`。R1 从授权建立隔离分支并 cherry-pick 候选，实际受检提交为 `8261d2a92ce2a09d3ba0b18a471ee5de92847861`。24 个交付文件与候选及 E1 索引逐字节相同，生产、配置、依赖、脚本及测试相对候选无差异。范围遵循[审核任务](../../coordination/tasks/P05_G4_DPO_R1.md)和[实现任务](../../coordination/tasks/P05_G4_DPO_CPU.md)。

## 必须修订

**P05-DPO-OUTPUT-001 / P2：返回 PASS 前没有把最终 summary 纳入输出上限。**

定位：[runtime.py](../../src/toolalign/training/cuda_dpo/runtime.py) 候选版本第 214、229–234 行。`supervise` 在收到子进程结果并回收后检查 `output_size(output)`，随后在 `finally` 中增加退出信息并写入 `summary.json`，写入后直接返回原 PASS。summary 包含完整身份等信息，其字节数可能使已接近上限的目录越界。

R1 原创 CPU 反例仅将模型 worker 换为可 pickling 的合成 worker；生产 `supervise`、spawn/Pipe、预算检查、文件写入和回收均实际执行。worker 写 60,000 字节合成产物，返回含 8,192 字符合成身份字段的终态。完整请求通过现有验证，结果为：

| 项目 | 实测 |
|---|---:|
| `max_output_bytes` | 65,536 |
| 最终 summary 写入前目录 | 61,185 |
| `summary.json` | 8,357 |
| 最终目录 | **69,542** |
| 返回状态 / summary 状态 | **PASS / PASS** |

worker 已正常回收，不存在遗留进程。预算断言实际 **1 failed / 0.29 秒**，原回执和全部文件保留。外层 export 的控制文件 allowance 不能证明 DPO 输出目录满足其自身 `max_output_bytes`。

最小整改：把最终编码后的 summary 和终态写入纳入预算计算，在返回 PASS 前确认完整输出满足上限；为失败回执预留空间，超限按 FAIL 留证。增加这一类“产物本身未超限、终态写入后超限”的定点回归，不需改动 DPO loss、数据或恢复循环。本轮不修改实现；该新问题由 S1 按 REVIEW_POLICY 登记并交 E1 修订。

## 已支持的实现判断

- D1/Q1 六文件重新经过 `apply_review`，保留原误标分母、已知误标排除和冻结顺序；synthetic 标记与零有效对不能进入正式训练。输入包不产生运行授权。原始 Action JSON 字符串保持，分别/拼接编码、EOS 和原生 prepared IDs 显式核对；超长对有 disposition，原分母不缩减。
- policy/reference 从同一选中 G3 step743 初始化，独立加载与逐键 adapter 校验；reference 全冻结/eval、adapter 启用。原生 Trainer 接收独立 reference 和 `peft_config=None`，没有使用禁用 adapter 替代 reference，也不复用 SFT optimizer。
- 数值、累积、保存与恢复沿用 TRL 0.26.2 / Transformers 4.57.6；实际安装源码确认 sigmoid、含 EOS 的 completion SUM 和实际尾组除数。AdamW 参数、常数 scheduler、SequentialSampler、完整一轮 `ceil(N/8)` 总步数及 optimizer 边界分段符合冻结协议。
- 完整 checkpoint 的完成标记在原生保存后写入，包含文件、身份、全局步数及游标；恢复检查 adapter/Adam/scheduler/RNG。容量 occurrence 计划与正式输入顺序、run_kind 身份分开，不能将容量 checkpoint 用作正式一轮起点。
- CUDA-only 入口、共享 GPULease、单卡/BF16 检查及 owned child 的外层进程组关系保持。既有 CPU 墙钟、输出中途超限和进程回收证据可复用；上面的终态预算缺口仍需修订。
- DPO 选择独立环境、锁和就绪记录；SFT/generation 仍走原环境与命令。实际重读 Mac 58 项安装版本全部匹配锁；Linux 69 包只有既有 Python3.12 dry-run 证据。两锁相对原依赖仅既有 fsspec 变为2025.10.0，满足 datasets 上界；生成后只有注释规范化，实际依赖/hash 内容一致。

## 独立 CPU 数值与恢复证据

R1 新建 **4,720 参数、3 对原创文本**的随机 Qwen3 类 fixture，未加载预训练模型。独立参考用无 padding 前向、FP64 逐目标 cross-entropy 和原始文本边界计算；未调用被测 DPO loss 或 E1 的参考损失函数。两条 `logits_to_keep` 路径均核对真实 attention、prompt/pad 零梯度、EOS、SUM 与全部 adapter 梯度，预定容差为 atol=2e-6、rtol=2e-5。

| 数值或行为 | 独立结果 |
|---|---:|
| 初始 policy=reference loss | 0.6931471824645996 |
| 非零 log-ratio 的 FP64 SUM 参考 loss | 0.6860301000108073 |
| 错误 token-mean 目标的对照 loss | 0.6930230114156783 |
| 原生两路径最大 loss 绝对误差 | 8.2431e-7 |
| 原生两路径最大 adapter 梯度绝对误差 | 2.0489e-7 |
| 实际 3 对尾组梯度相对独立均值参考的最大绝对误差 | 2.2352e-8 |

原始 synthetic adapter 与两份加载模型前向相同、存储独立；在独立副本上禁用 adapter 后最大 logits 差为0.213155，确认该对照能区别启用 SFT adapter 的 reference。实际原生训练完成一轮1步、尾组3对，仅 policy adapter 改变，policy 底座和 reference 全参数保持。CPU logits 为 FP32；CUDA AMP 下的实际 dtype 尚未测量。

R1 另核对 **81 份 E1 回执/原始状态文件**，直接读取最终 10 对运行的 checkpoint、梯度及 RNG，未重跑训练：新进程只消费最后2对，游标8→10；连续与恢复的4个 adapter、12个 Adam、4个尾组梯度张量最大差均为0，scheduler 和 Python/NumPy/Torch CPU RNG 相同。最终恢复及接口测试回执的22个源码/config/lock/test摘要与受检版本全部一致。

保留两类历史：E1 首轮原生测试2 passed/1 failed，失败为独立参考 optimizer 遗漏 scheduler 的 `initial_lr`；修后及最终恢复定点通过。R1 首次数值探针的禁用 adapter 负对照直接作用于 reference，PEFT 退出上下文时重设了其梯度标志；负对照移到独立副本后，原冻结断言保留并通过，候选实现未改。该探针最终 **1 passed / 2.44 秒**；已通过的恢复回读未重复运行。

复用 E1 的70项输入/进程/全部 Colab 检查和最终29 passed/1 skipped接口检查；唯一缺 pip parser 的 skip 已在其 Python3.12环境通过。没有重复安装、全量测试或10对训练。

私有 `evidence-index.json` SHA-256：`97aeb1e34e246a8f9006b99bc429a6a387263046815eea6e8fd2de5d96129519`，绑定31份本轮材料、原始失败、最终数值、源码与外部证据回读。复现入口见[交接](../../coordination/handoffs/P05-g4-dpo-review-r1.md)。本 DPO 包的真实 Qwen 前向、正式偏好编码、Linux/CUDA安装、容量/跨实例恢复及正式 DPO 均 **NOT_RUN**；本轮没有 GPU/Colab 操作、环境修改或共享状态写入。
