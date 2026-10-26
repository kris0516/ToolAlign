# P04 CUDA 实际容量数组：Q1-r1 增量复核

**PASS：固定 18 条 train 与 2 条 validation 的实际数组均通过。** 本轮 531 项检查无失败，原行、sidecar、20 个序列及完整 Batch 与预先固定的 cohort 对应；解码后的 prompt 和 completion 与批准原例及原 audit 一致。这批输入可支持 S1 按既定预算签发容量配置，实际 CUDA 结果另行审核。

2026-10-26；实际 reviewer：Codex-AI（Q1），独立 AI 对话，`gpt-6-astra / max`。精确执行源码为 `920c41551f0f7f2be8a5a8dcced23cc080ac1f27`，授权为 `594894d4dc8050f301eb8f419ee674ef43786b7c`。沿用 [13 例预审](P04_CUDA_MASK_Q1_R1.md) `82f1e88e168b80298c47455c26084cc9a4b54b92`；原数据质量判定与无关来源处置不重审。

## 精确实物

| 实物 | SHA256 |
|---|---|
| prepare 命令回执 | `1ad4692fac91716011d3bd3b886ba29170bb8556843b4ef540dc79841a8762b5` |
| encode 命令回执 | `94808db570e6e1f89a31118f797c9113476a586d18934ba91dbdaaf428234d32` |
| stage manifest | `4ae93d53a8490c0c21c307b75213344408afe9a42a9aafbf87838ccae61e0f0a` |
| arrays manifest，10,984 bytes | `fb429fe3767a5571f0c08369cf1c6705a0584ec11e83e0913a73dcfaa57a4536` |
| train 数组，790,488 bytes | `017d9ed1dfad71daf2be2192b59b1dffbe165df159bc8d384d992d69537eaa7e` |
| validation 数组，91,945 bytes | `7852256b10d27f9f48d02010ca43c5f064eb180b27c601460955a357967cd387` |
| 固定 cohort（canonical） | `48d66f48010dc0d0ce6db5bc64ac5e7223aa79fe7824f7ca623e6449f4adedeb` |
| 沿用的 13 例 review-arrays | `cc82ba3cc030ac990e741bd5fa0a735009f6cb2498ec0b1b30523daa1c3649d3` |
| 本轮逐例判断及 531 项检查 | `ba31264fb2433e09591246d67a527495110b53effa565ff6377fc69ca64d7bb9` |
| 本轮实际比较命令记录 | `5c9ed52231671190a17dfb9b5e51264b1fdfc029c95127e51e996509140c5c37` |

全部输入文件身份保存在私有 `inputs.json`；20 条逐例结论、原行/序列 hash、P/C/N、首末监督位置与理由保存在 `review-result.json`。20/20 为 PASS，未提出新增 issue。

## 核对结果与方法

1. **执行来源通过。** prepare 与 encode 的退出码均为 0，耗时分别为 80.87 秒和 2.13 秒；原 stdout/stderr 与回执 hash 一致。两次运行前后 741 个源码文件均与精确执行提交一致，stage/arrays 记录的 73 个包文件也匹配。prepare 实际暂存 20 条、新编码 0；encode 实际编码 20 条，stdout 与最终数组 manifest 对应。原编码命令包含已通过的 `read_bundle` 回读；Q1 另作完整数组比较，没有重新调用编码入口。
2. **选样与原行通过。** 两个 split 的每条数组均与对应 stage 原例绑定，两个版本的 sidecar 完整相等；原例的 canonical JSON 加换行得到原行 hash，Example、Action、模型输入及来源字段均与 audit 对应。实际 20 条 cohort entry 和原 rank 顺序逐项等于预先冻结草案，cohort hash 不变。
3. **mask 与移位通过。** 对每例令 P 为 prompt 长度、C 为不含 EOS 的 completion 长度，均满足 N=P+C+1。六组完整 Batch 数组、整数类型、右 padding、attention mask、loss mask 和一次 causal shift 均一致；监督分母为 C+1，首末 causal 监督位置为 P−1 与 N−2。20 个原 sequence hash 及各例其余六个未 padding 数组 hash 均匹配原 audit。
4. **文本与角色通过。** 核对固定 tokenizer 文件、版本、模板及 revision 后，只解码已有 token。20 例的 prompt 与 completion 各自匹配原 hash，连接序列的解码文本等于二者拼接；反解析原消息包装与工具目录，角色、消息顺序、历史调用/观察关联均保持，completion JSON 按类型等于原 Action。完整 prompt 的 loss mask 均为 0。
5. **13 例及消费者解释沿用。** 新 stage 中的 13 例 review 数组与上轮实物逐字相同；没有重跑原语义审阅。上轮静读的 11 个消费者、共享实现、配置及报告文件字节也未变化，原训练样本权重、验证 token 权重及容量诊断解释继续适用。

| 实际 split | 条数 | 未 padding 长度 N | 每例右 padding | 监督 token 总数（数组统计） | 结论 |
|---|---:|---|---|---:|---|
| train | 18 | 2044–2048 | 0–4 | 1,592 | 18/18 PASS |
| validation | 2 | 1851、1882 | 197、166 | 335 | 2/2 PASS |

全部 bucket 为 2048。满桶训练例保留 52 个 completion token 加一个 EOS，共 53 个监督目标。含两轮 assistant/tool 历史的验证例保留全部历史于 prompt，当前 completion 加 EOS 共 101 个监督目标；另一验证例为 234 个，因此本容量验证的总分母为 335。

训练消费沿用每样本 token mean 后按实际组长求 mean，容量组为 8+8+2。验证消费使用两个容量例的 CE sum/335。完整 formal profile 仍绑定 5,938 train / 213 validation；20 条只是容量诊断 cohort。manifest 的 `complete=true` 表示输入包写入完成，运行 summary 仍须标为 `diagnostic_only=true`、`validation_scope=capacity_cohort`、`epoch_complete=false`。本批输入不支持正式 epoch 或模型提升结论。

## 实际复核与边界

私有 `review-command.json` 保存完整绝对 argv、环境、退出码和输出 hash；公开命令中的 `CUDA_CPU_PYTHON` 指 S1 提供的既有共享 CPU Python：

```sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 RAYON_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 \
  "$CUDA_CPU_PYTHON" -B .toolalign-local/q1-p04-capacity-arrays-r1/review_arrays.py
```

实际 exit 0，进程约 0.452 秒，外部上限 300 秒；531 项检查全部通过。使用 tokenizers 0.22.2 作 60 次已有 token 解码，没有编码新序列，未导入 Torch、MLX、Transformers 或 PEFT。本轮首次完整比较成功，无新增失败；原审核与实现失败记录保持。

本轮 GPU、SSH、模型下载/加载/训练、环境或依赖安装均为 0。实际 CUDA 容量三步、完整 checkpoint 的新进程/新实例恢复、正式 SFT 和模型效果仍为 **NOT_RUN**。本结论完成容量输入的 Q1 门槛，后续配置与运行由 S1 按已定预算组织。
