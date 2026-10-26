# Q1｜G3 实际 SFT 数据与说明终验-r1

**PASS。两个 profile 均按已审完整数组完成一轮 SFT；全部 941 条训练记录、12 个完整验证点和所选 checkpoint 与报告、CSV、图一致。** Qwen3-0.6B 的验证 CE 从 0.739884032 降至 0.041493690，Qwen3-1.7B 从 1.145229556 降至 0.024437639。本轮支持各自冻结 validation 上 completion/EOS 拟合改善，数据与说明范围无阻断项。S1 可结合独立 R1 技术终验决定 G3 验收及 G4 接续。

2026-10-26。实际审核者：Codex-AI（Q1），`gpt-6-astra / max`。授权提交 `c658541bbf966c324353404ed3d964329e7c1670`；实际训练源码 `2abbe7ac913661df1d5e430f285604b4ceb8ff4b`。审核对象为 [S1 实测报告](../S1_P04_CUDA_G3_SFT.md)、发布 CSV/图、固定配置及已回收记录。Q1 未修改生产代码或共享协调状态。

## 已审输入的实际消费

复用本人 `98cf0e1370ff68ca3306e157be1f7c95ac37a2e9` 的[完整数组审核](P04_CUDA_SFT_FULL_ARRAY_Q1_R1.md)：两个实际 manifest 与已审副本逐字节一致，全部 run/config、summary、checkpoint 元数据绑定相同 profile、cohort、模型 revision、配置和源码。13 例材料身份随相同 manifest 保持，沿用 `82f1e88`、`ed022da`、`847e0be`，未重跑全数组、旧 531 项矩阵或重新标注。

| Profile | train / validation | 更新数 / 尾批 | 验证监督 token | SFT − 原始 CE | 所选 step |
|---|---:|---:|---:|---:|---:|
| smoke，Qwen3-0.6B | 1,583 / 194 | 198 / 7 | 21,226 | −0.698390342 | 198 |
| formal，Qwen3-1.7B | 5,938 / 213 | 743 / 2 | 23,841 | −1.120791917 | 743 |

smoke 在累计 100/198 步结束两段，formal 在 100/200/300/400/500/600/700/743 步结束八段。逐条核对 step、cursor、实际 microsteps 和 per-example loss，训练游标分别连续到 1,583/5,938，无重复或遗漏。每次续跑指向前段完整 state 的摘要，adapter 起点摘要与前段终点一致；前段外部回收完成时间早于下一段启动。这里核对记录、摘要和衔接元数据，张量内容与恢复技术验收由 R1 独立负责。

CUDA v2 配置 SHA256 为 `ee235d612b2552be5927b4ff790887a34b088ab842f78a15fcb8212323b60045`；G3 计划为 `f5fa66a3842ad0c4c3de2ef64f1aec8315c806fe6799078d207c07a1f8b46ff2`。

| Profile | 实际数组 manifest SHA256 | 所选完整 state SHA256 |
|---|---|---|
| smoke | `9a504ffd00b571eb5f5294d174d4285c92a695dee0d3171988d572185a860b5b` | `e29e650615be4dbb71ff4cb50d02ecca008ddde5901c496845bdc5a4da3eb51f` |
| formal | `58b59c6a47be9c768835dadf020a303c801909f8ad07b1875918ee2168170d58` | `cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14` |

## 数值、选模与解释

独立从事件记录重算每个 batch 的 `sum(per_example_loss) / microsteps`，941 行均与[训练 CSV](../experiments/p04-sft-g3/training.csv)一致。原始模型及每个 SFT 验证点的 `ce_sum / supervised_tokens`、样本数和分母逐项通过，并与[12 行验证 CSV](../experiments/p04-sft-g3/validation.csv)完整对应。smoke 的原始/step100/198 三点和 formal 的原始/八个 SFT 点全部纳入核对。

两份原始验证记录均在 step/cursor 0、adapter disabled 下使用同一完整 validation；续跑不重复生成原始点。按有限 CE、较早 step、checkpoint 摘要重选后，各段 summary 和 index 的历史最佳均一致，最终选择 step198/743。原始点未进入 SFT 候选，实际 bundle/消费者范围为 train 和 validation，未消费测试集。

训练值是每条样本自身监督 token CE 的 batch 平均；验证值按整个 validation 的监督 token 加权，包含 EOS 和一次 causal shift。[绘图脚本](../experiments/P04_SFT_G3_PLOT.py)采用相应 CSV 字段。已查看既有复画 PNG：四个面板标签清楚，验证纵轴明确为对数刻度，原始点与所选 SFT 标记准确。公开 CSV/SVG 与原分析文件仅有换行或行末空白差异；既有公开脚本复画 PNG 与原汇总 PNG 逐字节一致。

报告正确将两个 profile 的结果作各自模型内比较；数据规模、长度分布及验证样本不同，不能由两者 CE 高低直接推出模型容量优势。十段恢复是两次训练各自的连续分段；固定 seed 42，没有独立重复实验或多 seed 区间。工具语义、无需工具判断、故障恢复行为和独立测试效果留 G5，DPO 留 G4，报告未提前宣布全项目完成。

## 退出、回收、资源和失败历史

10 段均 exit 0、未超时。Q1 在接收时流式校验 196 个回收文件和 10 个归档的字节数及 SHA256，回收清单与停止前 inventory 一致；其中 18 个 `state.pt` 文件记录只做字节校验，未加载张量。summary 中 `remote_copy_verified` 与 `durability_verified=false` 保留原值，Mac 外部回收提供持久化证据。

重新汇总 6,269 条设备采样及 trainer 记录：smoke 用时 876.209522 秒，Torch peak allocated/reserved 为 2.150/3.787 GiB，设备观测峰值 4,174 MiB；formal 为 5,834.921909 秒、4.691/5.553 GiB、5,982 MiB，与报告取舍精度一致。设备值来自 1 秒间隔采样，不能视为连续测量的全局峰值。

各段绑定同一 L4 endpoint，回收先于停止；07:50:27 UTC 的停止记录为 `STOPPED_AND_ABSENCE_VERIFIED`，已绑定控制代码在写入该状态前核对 CLI 中实例不存在。07:51:08 UTC 账户记录为 0 active assignments、0.00 CU/hr。累计占用 9,124.538896 秒低于 14,400 秒上限；172.94→169.09 CU 的余额观测差 3.85 低于 8 CU 上限，报告未将它解释为精确账单归因。索引生成时私有产物 1,078,495,568 字节，低于 4 GiB 上限。

158 条已记录命令中，157 条绑定最终源码 `2abbe7ac`；04:24:38 UTC 的 `profile-stats-command` 绑定早期 `7eb0ac97e394528d82533c6cc92c298aa5d305b0`，其 778 个文件摘要与该 Git 提交一致。该命令只读冻结 sidecar 统计，模型和编码调用均为 0；随后 `9bfb2b8467e9bfefd5b98c6de4557a38f4684d40` 在计划中加入四个 train/validation token 分母字段，先于实际数组生成与 GPU 分配。这段历史不构成实际训练源码漂移。

唯一非零生产包装命令仍为首次安装 exit 1，其底层 SSH 为 exit 255 / Broken pipe；原远端安装进程随后 exit 0，锁定依赖和 pip check 通过，无重复安装提交。G2 原 FAIL 和零更新诊断保持原结论。完整 SFT 的底座内容全量摘要保持 `NOT_RUN`，本审核未把复用 G2 冻结/optimizer 绑定证据写成新增全量内容校验。

## 独立证据与交付范围

私有入口为 `.toolalign-local/q1-p04-cuda-g3-final-r1/`。原 S1 索引 SHA256 为 `be10313e0c200dde1a8c2c4660842a3d2474d9210ab7d01bda2cc506cecef544`；本轮输入索引为 `dac9436b73f33b489bcd679cc7ff42eadb3a0aacce2ae606be995462e204940c`。

| 记录 | SHA256 |
|---|---|
| 最终机器核对 `review-final-result.json` | `1ae5741e29cd4816720ce7306f93d82faf6a532384d896868a2f2bbab1dacab3` |
| 原始核对 `review-r1-result.json` | `895197aa6149b0049a55195b973dec13c3afa5720ac35ee721baa29eaa545553` |
| 来源补核 `source-receipts-r2-result.json` | `5ac2e9346e7c7d8ca17b52662ae7f5906aad5426880274d4311cd6ae5b921445` |
| 图像、源码与解释审阅 `manual-review.json` | `135a2811d13eb4ebf2afad9de1dcf0d6bcfff6f27539ce01f6e0c9aa4af688e3` |

Q1 首次辅助检查误将早期统计命令也要求为最终训练提交，产生一项来源断言失败；原输出和 helper 均保留。确认实际时间线后，仅补核每条命令自身记录的 Git 身份，复用其余 179 项已通过核对，最终 PASS；未修改生产证据。这不属于生产候选的正式修订失败，不建议新增问题计数。

两条独立核对命令分别耗时 0.178/0.193 秒，限制均为 300 秒、2 线程；本次新增私有产物小于 35 MiB，上限 200 MiB。模型、GPU、SSH、tokenizer 编码、安装和旧质量矩阵重跑均为 0。公共交付仅本报告与[Q1 交接单](../../coordination/handoffs/P04-cuda-g3-final-q1-r1.md)，由 S1 维护阶段状态。
