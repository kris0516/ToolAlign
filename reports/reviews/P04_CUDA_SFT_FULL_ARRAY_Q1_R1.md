# G3 完整 SFT 数组：Q1-r1 增量审核

**PASS：smoke/formal 两套实际数组共 7,928 行全部对应冻结 v3 选择。** 未发现重复、漏选、额外样本、截断或监督边界差异。独立累计的 validation 分母为 **21,226 / 23,841**，支持 S1 按既定 G3 计划冻结运行配置。该结论完成全量输入的 Q1 门槛；完整 SFT 与模型效果仍为 NOT_RUN。

2026-10-26；实际 reviewer：Codex-AI（Q1），独立 AI 对话，`gpt-6-astra / max`。授权及实际执行提交：`2abbe7ac913661df1d5e430f285604b4ceb8ff4b`，范围见[任务包](../../coordination/tasks/P04_CUDA_SFT_FULL_ARRAY_Q1_R1.md)。生产代码与 R1 已审候选 `c633bd70f4446bc8ea3ee80440944e6e6da7ff87` 一致，原 R1 审核为 `fd4ad07cb4a6a083c5fc178ba30a5705cc2a9684`。既有 PR26 / CI 40271208505 的双 Python 成功记录及发布材料已绑定。

## 实际覆盖与监督分母

下表来自实际 `causal_loss_mask` 的独立累计；长度 N 包括单个追加 EOS。bucket 列为 1024 / 1536 / 2048 三档的行数。

| Profile / split | 实际行数 / 通过 | 监督 token 总数 | N 范围 | bucket 行数 |
|---|---:|---:|---:|---|
| smoke train | 1,583 / 1,583 | 141,211 | 747–1536 | 424 / 1,159 / 0 |
| smoke validation | 194 / 194 | 21,226 | 783–1519 | 74 / 120 / 0 |
| formal train | 5,938 / 5,938 | 536,238 | 747–2048 | 977 / 2,598 / 2,363 |
| formal validation | 213 / 213 | 23,841 | 783–1882 | 74 / 120 / 19 |

逐行同时读取冻结的 example、sidecar、实际 stage 与实际 arrays，确认 ID、原始行字节摘要、连续 rank、顺序和完整 sidecar 一致。四份实际 ID 序列的 canonical hash 均匹配冻结 selection manifest 和 CUDA v2 配置；每个 profile 的 train/validation ID 不相交。只读取这两个 split 的选择数据，未读取测试集 payload 或用测试集选样。

每行独立核对 17 类关系：原例/Action/model-input 绑定、格式身份、数组整数类型、P/C/N、最小可容纳 bucket、单 EOS、完整右 padding、attention/loss mask、一次 causal shift，以及七项未 padding token/mask 摘要。P 为 prompt token 数，C 为不含 EOS 的 completion token 数，均满足 `N=P+C+1`；prompt 与 padding 的监督为 0，completion 加 EOS 的监督为 1，首末 causal 监督位置为 `P−1` 和 `N−2`。完整 Batch 与独立构造的预期数组一致，各 token 摘要匹配原冻结 audit；没有重新编码或调用 tokenizer 回调。

smoke 使用固定 Qwen3-0.6B revision `c1899de289a04d12100db370d81485cdf75e47ca`，上下文上限 1536；formal 使用 Qwen3-1.7B revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`，上限 2048。两套实际 tokenizer 的文件、模板、repo/revision 和编码设置与记录对应。

两套 13 例 review-arrays 的实际内容 SHA256 均为 `cc82ba3cc030ac990e741bd5fa0a735009f6cb2498ec0b1b30523daa1c3649d3`，与 Q1 留存实物一致。因此复用 [82f1e88 预审](P04_CUDA_MASK_Q1_R1.md)、[ed022da 增量审核](P04_CUDA_CAPACITY_ARRAY_Q1_R1.md)和 [847e0be G2 终验](P04_CUDA_G2_FINAL_Q1_R1.md)中的适用语义结论；未重跑旧固定 20 例的 531 项矩阵或重新标注。

## 执行绑定与生产口径

四个 prepare/encode 回执均为 exit 0，原 stdout/stderr 摘要匹配；执行前后 785 个源码文件与精确执行提交一致，stage/arrays 中 73 个包文件也对应。CUDA v2 配置 SHA256 为 `ee235d612b2552be5927b4ff790887a34b088ab842f78a15fcb8212323b60045`。两个数组 manifest 的 stage 绑定、冻结 data binding、模型/profile 和 cohort 均通过核对。

| Profile | prepare 秒 / 新编码 | encode 秒 / 新编码 |
|---|---:|---:|
| smoke | 79.692 / 0 | 20.290 / 1,777 |
| formal | 80.931 / 0 | 77.983 / 6,151 |

原请求时限分别为 prepare 300 秒、encode 1200 秒，实际均在时限内；产物均满足各自 512 MiB 上限。S1 原完整回读为 exit 0、3.112 秒，其源码与证据绑定通过。Q1 另行核对了全部实际行及原冻结选择，未重新运行生成入口。

静读当前消费者确认：训练先取每例 completion+EOS token mean，再按实际 microsteps 求均值；表中 train token 总数为统计量。验证使用完整冻结 validation 的 CE sum / 监督 token 总数。新增原始模型验证关闭 adapter 后调用同一 validation reader 与 `evaluate`，不进入 SFT checkpoint 选模。按实际 train 行数与累积组长 8 推导，一轮为 smoke 198 次更新、尾组 7 条；formal 743 次更新、尾组 2 条，与计划一致。这些是输入及计算口径结论，实际训练结果另审。

## 原始证据与本轮命令

| 证据 | SHA256 |
|---|---|
| 冻结输入 manifest | `08e865ff98bd476c94153033bc192664d72cee64443184576532c0289a610dd7` |
| S1 完整数组索引 `full-array-readback.json` | `533752d2223111f3476cd9b04f4ab8d5632d03ff8954f76a9dbb373931edb5ab` |
| smoke arrays manifest | `9a504ffd00b571eb5f5294d174d4285c92a695dee0d3171988d572185a860b5b` |
| formal arrays manifest | `58b59c6a47be9c768835dadf020a303c801909f8ad07b1875918ee2168170d58` |
| Q1 `review-r1/result.json` | `76b84c1405235ca6176bb89d13d5c74b0589bc5d15040a1aa3fc8e24ce47f025` |
| Q1 7,928 行逐行结果 | `c6fdf943ef4f053e0deb54832c93b6546749d381c5e40f3a319406ca411a9133` |
| Q1 实际命令回执 | `6be4bfa82514a1c515fb23bed4d17ec31899f84f7d45a35b17c3eee72f5ba40e` |

私有证据位于 `.toolalign-local/q1-p04-cuda-sft-full-array-r1/`。71 个实际输入路径完成字节数/hash 核对，137 项文件、来源及汇总核对全部通过。逐行结果仅保存 ID、rank、边界、摘要和判定；大型数组、stage 和冻结选样文件均只读流式检查，没有复制整套输入。本轮新增私有产物约 4.7 MiB，低于 256 MiB。

实际命令使用已有系统 Python 和标准库，外部 timeout 为 300 秒，四项线程上限均为 2：

```sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 \
PYTHONDONTWRITEBYTECODE=1 \
  python3 -B .toolalign-local/q1-p04-cuda-sft-full-array-r1/review_full_arrays.py review-r1
```

首次完整核对 exit 0，命令用时 14.164 秒；7,928/7,928 行与全部汇总项通过，无新增 issue 或失败。新增模型加载、GPU、SSH、编码及安装均为 0。公开改动限本审核报告与交接；正式状态及运行配置由 S1 维护。
