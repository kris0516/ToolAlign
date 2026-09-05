# P01｜本机兼容性与容量校准

2026-09-06；T1 自测候选，**待独立 R1 与 S0 验收**。实现提交 `eed03e88d5cc88f6db8b3845f2e7d5c9967c9c02`，集成公共基线 `a6c8dd3c78b3674a242b4faacbb175f7b7c98303`。本报告不代表 P04/P05 正式训练、完整评测或服务部署。

本机原始 Qwen3-0.6B 的受限 SFT、唯一备选 DPO、保存重载通过自测；Qwen3-1.7B 的 1024/1536/2048 档最终运行通过。首选 mlx-tune DPO 未通过；备选也只在明确修正监督 mask、全进程禁用编译优化、冻结完整 SFT reference 的配置下通过。所有失败保留。

## 1. 证据与环境

- [P01_RESULTS.json](P01_RESULTS.json)：10 次运行的实际 commit/source hash、退出码、资源、计数、指标和原始证据 SHA-256。
- [P01_PREREGISTRATION.md](P01_PREREGISTRATION.md)：每轮运行前的预算、数值门槛及修订理由。
- [P01_ENVIRONMENT.json](P01_ENVIRONMENT.json)、[源码身份](P01_SOURCE_IDENTITIES.json)、[88 包探索清单](P01_EXPLORATION_REQUIREMENTS.txt)：版本、PyPI 来源、wheel 与关键源码 hash。探索清单是实测环境记录，不替代 S0 的公共锁文件。
- [P01_VALIDATION.json](P01_VALIDATION.json)：最终 CPU/打包检查的命令、退出码和原始日志 hash。

实际硬件：Apple M5 Pro，16 GPU cores，15 CPU cores（5 performance + 10 efficiency），51,539,607,552 bytes = 48GiB，macOS 26.5.1 / 25F80，arm64，Python 3.14.7。MLX/Metal 的可执行性来自本轮受锁模型运行；其他机器、Python 版本和长时间热稳定性未验证。

原始未量化 BF16 模型只下载公开、未 gated 的官方仓库：

| 模型 | 固定 revision | 许可 | 下载口径 |
|---|---|---|---|
| [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B/tree/c1899de289a04d12100db370d81485cdf75e47ca) | `c1899de289a04d12100db370d81485cdf75e47ca` | Apache-2.0 | dry-run 权重约 1.5GB |
| [Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B/tree/70d244cc86ccca08cf5af4e1e306ecf908b1ad5e) | `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` | Apache-2.0 | dry-run 权重约 4.1GB |

运行前重新计算下载文件 SHA-256，并核对本地 Hugging Face revision/LFS 元数据。run.v1 绑定实际模型、adapter、tokenizer、template 和源码身份。原始训练内容、逐 token 审计、权重、adapter、配置及日志仅保留在私有目录。公开统计由报告脚本抽取；脚本逐个验证冻结 manifest 内制品的相对路径、大小和 hash。math-r1 是早期未提交代码的小张量检查，git_commit 仅指当时基线，精确代码以 source hash 为准；正式数值结论使用已提交实现的 math-r2。

## 2. 实际计算路径与依赖申请

实测核心版本：mlx/metal 0.32.2、mlx-lm 0.31.3、torch 2.14.0、psutil 7.2.2、numpy 2.5.2、transformers 5.16.1、huggingface-hub 1.30.0。公开 compatibility extra 在上述公共基线只直接锁定 MLX、MLX-LM、PyTorch、psutil；没有批准 DPO 库。PyTorch 分发包声明复合 SPDX，见公共环境说明，不能简写为单一 BSD。

向 S0 提交的分组职责如下，**此表不是已合并依赖声明**：

| 分组 | 直接依赖与平台建议 | 职责与限制 |
|---|---|---|
| compatibility（已存在） | 公共锁中的 MLX/MLX-LM/torch 使用 Darwin arm64 marker；psutil 同公共锁 | SFT/数组与独立 CPU 参考的环境基础 |
| dpo（待 S0/R1） | `mlx-lm-lora==3.1.2`，`datasets==3.6.0`；Darwin arm64 marker | 唯一备选候选；前者许可元数据不一致，见下文，后者 Apache-2.0；安装不表示正式 DPO 已通过 |
| p01-replay（待 S0/R1） | `mlx-tune==0.6.0`；Darwin arm64 marker；同时选择前两组 | Apache-2.0；复现首选负例和跨库重载审计；首选 DPO 仍失败 |

固定版来源：[mlx-lm-lora](https://pypi.org/project/mlx-lm-lora/3.1.2/)、[datasets](https://pypi.org/project/datasets/3.6.0/)、[mlx-tune](https://pypi.org/project/mlx-tune/0.6.0/)。本机验证为 Python 3.14.7；marker 不等于其他 Python/macOS 组合已测。未约束 datasets 的新解析会选 5.0.1，并改变 dill/fsspec/multiprocess；本轮实际为 datasets 3.6.0、dill 0.3.8、fsspec 2025.3.0、multiprocess 0.70.16，应由 S0 将传递锁与探索清单核对。

实装 LICENSE 审计：mlx-tune 0.6.0 的 metadata 和 wheel 均为 Apache-2.0，早期 MIT 口头记录已更正。mlx-lm-lora 3.1.2 metadata 的 `License` 为 MIT，但 wheel 自带 `dist-info/licenses/LICENSE` 为 Apache License 2.0；该不一致待 S0/R1 核对，不能笼统写 MIT 或把第三方内容重标 MIT。环境 JSON 同时保留 metadata 字段、wheel LICENSE 相对路径和 SHA-256；本轮未复制第三方实现或上传制品。

当前完整 `math`、`smoke`、`calibrate` 仍会导入 mlx-tune：数值入口重放失败首选负例，模型入口先调用 `MLXModelWrapper.load_adapter` 做跨库审计，再检查 `mlx_tune.losses.dpo_loss`，最后进入唯一备选。**仅 compatibility 或 compatibility+dpo 不能运行完整 P01 replay**。没有为打包更改已经测过的 GPU 路径；将来正式 backend 不应继承审计依赖。

SFT 使用原生 `mlx_lm.tuner.trainer.train`，注入显式 completion loss 与 batch iterator。备选使用原生 `mlx_lm_lora.trainer.dpo_trainer.train_dpo`、`get_token_scores`、`dpo_loss`、AdamW；因其没有 iterator 注入参数，只在专属进程内临时替换模块 iterator，`finally` 恢复，训练循环/optimizer 不自建。先冻住底座，只解冻 LoRA A/B；用训练器实际回调和 optimizer.step 包装记录真实微步/更新数。目标为 28 层 Q/V，rank 8、scale 2（alpha 16）、dropout 0。SFT Adam LR 1e-4；DPO AdamW LR 5e-6、beta 0.1、sigmoid、求和 completion logps；accumulation 8，拒绝不完整累积周期。

上游 wired-limit setter 请求在作用域内仅记录，真实 setter 不调用；没有抬高系统限制。完整备选进程从模型加载、SFT、reference 预计算到 DPO/重载都调用官方诊断开关 `mx.disable_compile()`；编译模式、依赖和 checkpointing 配置进入 reference 身份。1536/2048 的 DPO 使用原生 gradient checkpointing；SFT 未开启。它们都是明确的兼容性条件，不能泛化为默认库配置通过。

## 3. 监督语义、数值与冻结 reference

32 条原创 train-only smoke 样本覆盖工具调用、工具 observation 后的 assistant 决策、no_tool、clarification，每类 8 条。不是 P02 数据，也未读取 BFCL/final test/oracle。非 thinking 模板；整段 prefix+completion 联合 tokenize，断言 prefix 的 BPE token 边界稳定；不截断。每条只监督一个 assistant 决策，保留一个监督 EOS。T1 抽查实际 token 表前 12 条（覆盖四类）；kris 的人工语义确认 **NOT_RUN**。

`completion_mask[i]` 表示 token[i] 是否受监督。计算用输入 `ids[:-1]` 预测目标 `ids[1:]`，loss mask 同时取 `[1:]`；prompt、工具 observation 和 padding 不计 loss。原生 fallback 的 mask 对齐到 logit 位置，因此显式 collator 将 token mask 移为 `mask[1:] + [0]`。microbatch 1 的 chosen/rejected 分别按真实完整长度输入，避免无必要的共同补齐；样本内容未修改。

math-r2：MLX CPU 与 PyTorch CPU，float32，所有 absolute tolerance 2e-6；PyTorch 使用独立 ignore_index CE / log_softmax+gather / softplus 实现，未默认使用 MPS。

| 检查 | loss 绝对误差 | 最大梯度绝对误差 | 自测 |
|---|---:|---:|---|
| completion CE | 1.1920928955e-7 | 1.4901161194e-8 | PASS |
| 标准 summed-completion DPO | 5.9604644775e-8 | 1.8626451492e-9 | PASS |
| **真实备选** get_token_scores + dpo_loss | 1.1920928955e-7 | 1.8626451492e-9 | PASS |

policy=reference loss 为 0.6931471824645996；扰动忽略位置 logits、增加右 padding 后 CE 不变。chosen/rejected 梯度方向正确。真实上游负例也被复现：MLX-LM 默认边界把应为 2 个监督 token 计成 3 个，loss 2.2351944447 vs 正确 2.4306473732；备选默认 mask 计入首个 padding 预测；mlx-tune 省略固定 reference 时 stop-gradient policy 随 policy 变化，loss 持续 ln2，不能代表冻结参考。

源码审计另发现 mlx-tune `ref_model` 参数未在对应训练路径使用、accumulation 配置未应用。这两项标 **SOURCE_ONLY**，没有运行其训练器去证明实际更新次数。首轮模型门槛失败后不执行它的 DPO 更新。

reference 是独立模型对象，包含真实 SFT smoke adapter，所有参数冻结。先核对所有参数 hash 和前向，再预计算；DPO 后重复核对全部 reference 参数与输出，policy 只允许声明的 112 个 adapter arrays 改变。关闭 adapter 会回到底座，不是 SFT reference。正式 DPO 必须使用 `accepted_sft` 身份；本轮明确允许 `sft_smoke`，未把 smoke checkpoint 冒充已验收 P04。

跨库真实 loader 的 adapter metadata、target paths、所有参数 hash、非 thinking template、首决策全词表 logits、抽样 completion logps 和 greedy IDs 对照通过；logits/logps 实际最大差 0（容差 1e-5）。备选真实 loader 的 SFT 导入、DPO adapter 保存重载也达到全参数 hash 相同和 logits 差 0。未验证任意第三方 adapter 或其他 target modules。

## 4. 全部运行与负结果

下表简称省略 `p01-`；精确完整提交、source hash、run/config/stdout/steps 等 SHA-256 见结果 JSON。退出码表示进程结果，**不能代替数值验收**。

| run | 提交 | 退出码 | 实际 SFT 微步/更新 | 实际 DPO 微步/更新 | 最终证据判定 |
|---|---|---:|---:|---:|---|
| math-r1 | ebcaf58 + source hash | 0 | — | — | 早期 CPU PASS |
| math-r2 | aaab75e | 0 | — | — | CPU PASS，含真实备选独立梯度 |
| smoke06-r1 | 3f55ecf | 0 | 32/4 | 0/0 | SFT PASS；首选 DPO FAIL |
| smoke06-r2 | 45f4670 | 0 | 32/4 | 8/1 | **FAIL_TRAINING_PATH_LN2** |
| smoke06-r3 | a2df878 | 2 | 32/4 | 0/0 | reference score gate FAIL |
| smoke06-r4 | 59f80f7 | 0 | 32/4 | 8/1 | 修正后备选 PASS |
| calibrate17-1024-r1 | aaab75e | 0 | 112/14 | 8/1 | PASS |
| calibrate17-1536-r1 | 47c0340 | 124 | 112/14 | 0 已记录/0 已记录 | 系统 pressure=2，STOPPED_RESOURCE |
| calibrate17-1536-r2 | fdb37c7 | 0 | 112/14 | 8/1 | DPO checkpointing 后 PASS |
| calibrate17-2048-r1 | f60ff10 | 0 | 112/14 | 8/1 | PASS |

smoke06-r1 原生 mlx-tune BF16 full-reference/shared-completion 初始 DPO loss 为 [0.9140625, 0.69140625]，第一项超出运行前 ln2±0.02 门槛，DPO 更新 0。显式 float32 参考通过不抵消该原生失败。

smoke06-r2 的预检查 ln2 通过，但实际编译训练路径在首次更新前出现 0.6945998073 / 0.6798114181，违反严格 2e-6。旧程序 JSON 的 PASS 原样保留，报告脚本通过真实 steps 独立降级；不是有效 DPO 通过。后续新增每个首次累积周期训练 loss 门槛。smoke06-r3 在 reference cache 建成后才禁编译导致 reference score 对照失败；具体差值未捕获，标 **NOT_CAPTURED**。结果中 legacy primary_dpo 不是该退出的直接原因；以 failure/stdout 为准。

smoke06-r4 全进程保持同一编译模式，首次实际训练的 8 个 loss 全部为 0.6931471824645996，更新后两对 loss 为 0.6378837228 / 0.6501557827。SFT loss 1.2343043025→0.1848807018；总 421 个监督 token、10,054 个逻辑处理 token、40 微步、5 次更新。所有底座/reference 冻结、adapter-only 和重载检查通过。短样本训练 loss 下降仅证明功能路径，不能证明泛化效果。

1536-r1 在 159.98 秒附近系统 pressure=2；swap 比启动增加 33,161,216 bytes，未达 1GiB。实际停止因压力，不能写成 MLX OOM；外层终止并回收自己的 child，保存已有 SFT 检查点。pressure 恢复为 1 后重跑。后续成功档 pressure 正常、swap 增长 0。系统压力是整机信号，未将它归因于其他进程。

## 5. 1.7B 容量、时间与有限外推

输入通过重复原创上下文扩展到约 bucket−64，然后 SFT pad 到 bucket；它是容量探针，不是 P02 长度分布。每档 112 SFT 微步中前 8 暖机、后 104 同步计时（满足至少 100 个可测目标），14 次更新；DPO 另 8 微步/1 次更新。没有将 microstep 当 optimizer step。

| 最终 bucket | SFT mean ± sample SD 秒/微步 | SFT 104 步秒 | DPO 8 步总秒 | MLX peak GiB | RSS peak GiB | 全进程秒 |
|---:|---:|---:|---:|---:|---:|---:|
| 1024 | 0.559896 ± 0.004995 | 58.229 | 11.855 | 17.649 | 11.774 | 110.567 |
| 1536 | 0.886035 ± 0.005920 | 92.148 | 22.198 | 14.435 | 12.417 | 166.469 |
| 2048 | 1.480036 ± 0.108073 | 153.924 | 40.022 | 17.987 | 11.690 | 273.427 |

MLX allocator 与 OS RSS 统计对象、采样时机不同，不能相加或把 RSS 当 GPU 独占内存。统一内存共享给 CPU、GPU、系统和应用；48GiB 不是模型独占预算。1024 未开 DPO checkpointing，1536/2048 开启，不能把不同档的峰值差简单归因于序列长度。

| bucket | reference 预计算秒（2 对） | SFT 验证前/后秒（32 条） | SFT/DPO checkpoint 写入秒 | 生成 2 请求：prompt→output token | 生成墙钟秒/请求 |
|---:|---:|---:|---:|---|---|
| 1024 | 0.727 | 5.773 / 5.789 | 0.00846 / 0.00577 | 941→19 | 0.507 / 0.509 |
| 1536 | 1.114 | 8.782 / 9.064 | 0.00331 / 0.00381 | 1453→19 | 0.591 / 0.594 |
| 2048 | 1.799 | 14.209 / 14.760 | 0.00604 / 0.00497 | 1965→19 | 0.795 / 0.800 |

checkpoint 计时包装真实上游 safetensors 写入并同步；没有做 fsync/冷缓存持久化 benchmark。SFT iterator 微步计时与 checkpoint I/O 分开登记，trainer 总耗时还含回调/验证/保存开销。DPO 首个暖机分别 1.734/2.731/4.814 秒，余下 7 步分别 10.092/19.441/35.177 秒；样本太少，不能当稳定正式 DPO 吞吐。

生成是 SFT 与跨库重载各一个 greedy 请求，每请求上限 32 新 token；没有正式偏好挖掘。上游报告 prefill throughput 约 4,985–5,600 token/s、decode 约 59.5–75.2 token/s，原始值逐请求见 JSON；墙钟还含其他开销，二者不能直接拼成完整任务延迟。P03 完整任务执行、工具等待、256-token 输出协议的 TTFT/端到端延迟 **NOT_RUN**。

按同档实测 SFT 最小/平均/最大微步耗时线性乘 1000，给出乐观/中间/保守**局部计算估计**：

| bucket | 每 1000 SFT 微步：乐观/中间/保守分钟 |
|---:|---:|
| 1024 | 9.14 / 9.33 / 9.60 |
| 1536 | 14.57 / 14.77 / 14.98 |
| 2048 | 21.82 / 24.67 / 27.87 |

这不是置信区间或运行时上限。正式估计应按实际 bucket 比例计算 `sum(n_bucket × measured_mean)`，另外计暖机、validation、reference、generation、checkpoint、资源重试。此处没有正式训练规模和真实数据分布，未给十天完成承诺。热量、功耗、长时间频率变化、其他负载、长输出和 checkpoint 恢复会改变耗时。不得据短 smoke 结果增加预算或启动 P04/P05。

## 6. 资源边界、CPU 与打包

模型导入前取得共享 GPULease，直到专属 worker 退出并释放模型驻留/OS flock。外层每秒仅监控自己启动的 child；最长 900 秒、MLX 24GiB、RSS 30GiB、swap 增长 1GiB、非正常 pressure 即停止；校准至多 120 微步/524,288 个逻辑处理 token，私有磁盘上限 20GiB。最长档实际 260,964 个逻辑处理 token（含 pad），253,796 非 padding token，1,120 监督 token，15 次更新。reference/validation/generation 的计算不计入训练逻辑 token，已通过独立次数/墙钟限制；这些计数也不声称包含所有激活重算 FLOPs。

MLX 峰值在同步工作单元之后检查，RSS 每秒采样，不能排除单个单元内的瞬时峰值。异常只保证已写出的 checkpoint；`weights_only_restart`，没有 optimizer/RNG 完整恢复。租约竞争、超时不加载、错误释放、mask/EOS/padding、reference 原始底座/身份变化、scaling 和重载偏差的 CPU 正负例均测试；租约测试用独立临时 Git 仓库，不竞争实际 GPU 租约。274 项总 CPU 检查通过，其中 P01 41 项，含已有独立审查测试；不将它们算作模型 benchmark。

wheel 构建、隔离安装、无 ML 依赖导入与契约 CLI 检查通过。**公共 sdist 边界发现尚待 S0 修复**：在 `.git` 为文件的 App worktree，Hatchling 1.27.0 只读枚举实际选中 29,241 文件 / 7,128,391,528 bytes，其中 29,116 个在私有目录；数字会随私有日志增加。复现脚本 [P01_CHECK_SDIST_SELECTION.py](P01_CHECK_SDIST_SELECTION.py) 退出 1，不创建 archive。先前完整 `uv build` 在 sdist 压缩阶段被 T1 停止，未产出 sdist、未上传；仅 `uv build --wheel` 成功。根因可能与 worktree VCS 忽略发现有关，**推断，未确认**。S0 已接管显式 sdist 选择规则及独立审查，T1 未修改公共 pyproject。

## 7. 尚未执行或验收

独立 R1/S0 验收、kris 人工样本语义确认、公共 p01-replay 环境对整条 GPU 路径的复跑、正式 SFT/DPO、正式偏好生成、完整 P03 harness、BFCL/最终测试、长时稳定性/功耗、跨机器验证和服务部署均 NOT_RUN。mlx-tune 原生训练未通过；备选默认 padding/编译配置没有通过，必须保留上述条件。sdist 问题由 S0 集成修复后复核。没有模型/数据上传、付费资源或公网接口。
