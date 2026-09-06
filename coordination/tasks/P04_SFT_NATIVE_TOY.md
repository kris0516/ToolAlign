# P04-SFT-NATIVE-TOY｜原生 GPU 尾周期与状态绑定验证

状态：READY_FOR_REVIEW。完整候选`f7326d1823c4cf132ae44525f4755c96c88ec159`已普通推送并由S0核验；T1原轮completed/idle，三次框架运行/完整1050CPU自测及原始制品已交付，独立R1仍待验收。以下保留T1完整`de86568d73ee77bbf92b6f749a39a9ab38955836`原授权。S0 依据 ADR-0021 授权一个新的有限数值子包；CPU 准备已 VERIFIED，完整 P04 和人工门槛保持未完成。

| 字段 | 本轮值 |
|---|---|
| owner | T1，复用已结束上一轮的独立 Codex 任务及隔离 worktree |
| code_base | `50867c0be43d110df6c3620c94022fcfdaf779b5`，PR10 main 验证发布提交 |
| authorization_commit | S0 原生分发给出的本任务完整协调 SHA，切换前读取并保留私有副本 |
| 新 branch | `work/p04-sft-native-toy`，从精确 code_base 新建 |
| 模型/推理 | `gpt-6-astra` / `max`；禁止创建其他任务或 sub-agent |
| 配置原件 | [P04_SFT_NATIVE_TOY_CONFIG.v1.json](P04_SFT_NATIVE_TOY_CONFIG.v1.json)，SHA-256 `fb06634d00b0565a60dc22ea829ac509732b3b6429b9bbbc2ff6207c974850cb` |
| 交接 | `coordination/handoffs/P04-sft-native-toy-r1.md` |

先读授权提交的 AGENTS、PROTOCOL、PROJECT_STATUS、本任务、配置原件、ADR-0021、docs/03 与 docs/16，以及 [PR10 main 证据](../../reports/S0_P04_SFT_CPU_MAIN_VERIFICATION.md)和原 [CPU 入口限制](../../reports/experiments/P04_SFT_CPU_UPSTREAM_LIMIT.md)。新范围使用 MLX 的 GPU 执行和独立 PyTorch CPU 参考，验证原生上游接口；不宣称修复上游 CPU 支持，也不从 CPU PASS 推导正式训练许可。

## 输入、所有权与保全

切换前确认旧本地 `work/p04-sft-cpu` 仍为 `33d6248e2c518ea777618224382bd30a3cc3433d`、旧 P01 分支仍为 `9fe3cbe3a067725c37dc213bbf38f9c90ceb5066`，工作区干净。新建分支时保留原 refs、旧 P01/P04 全部制品及两次 CPU 失败；不推进或推送旧 CPU 分支覆盖较新远端。原 R1 审查 `800480b0b1e14c21937f1b5073daf543a2ba31fc` 保持。

仅允许修改 `src/toolalign/training/sft/mlx_adapter.py` 和 `validation.py`，新增 `src/toolalign/training/sft/native_toy.py`、`tests/training/sft/test_native_toy.py` 及必要原创小 fixture、新 `reports/experiments/P04_SFT_NATIVE_TOY_*` 和本轮 handoff。允许将 CPU/原生 GPU 共用的有限适配提取为内部函数；原公开 CPU 函数的默认行为、CPU 设备限制和默认 CLI 保持。validation 只增加精确 `TOY_NATIVE_GPU` scope/profile，拒绝 scope/profile 不一致以及 CPU/GPU score 混选；不放行 formal score。

唯一新配置例外为 `configs/sft-native-toy.v1.json`，逐字节复制上述 S0 原件，调用时核对完整文件 hash。S0 拥有配置值和变更权。原 CPU 配置、training-data、selection、contracts、依赖/环境/CI、model_io/data/P01/P03、原测试/报告/审查及 S0 协调文件全部只读。消费代码 hash 随真正的源变更形成新 epoch，不能改写旧 CPU prepare `52cd77a0…` 的提交/时间/hash，也不能把新 native 源遗漏于其消费身份。

只写本轮新私有目录，累计最多 2 GiB；已存在的运行目录不得覆盖。使用旧 T1 两次 CPU 运行中相同的原创输入原件，文件 SHA-256 为 `df4b87001074e9fab6c3a330cf516dca17cfab1bb7505d97025ceeb31d3b5b47`：13 例、词表 8、8×8 的 64 个 float32 参数、padding 桶 16、EOS 7、pad 0。输入生成代码原 hash 为 `3872ed4187b0754b9baa32525a6aa3b157e33c0d7ceb7b9d1336f34df4536ed0`。核对全部原 token/attention/loss mask、shift、顺序和初始值；新记录可以另列 native scope，但原件字节不改。不得用任意同尺寸数据取代固定原创输入，不重新编码实际 P02 10+3 例或 8,228 行，不重新物化选择。真实语义/token-mask 填写表保持由 kris 填写。

## 原生接口与设备

本轮新增明确的 native toy 入口，仅接受已核对配置与固定原创输入；默认安装包导入/CPU prepare 仍不导入可选框架。检查实际共享租约后才导入 MLX/Torch，先设置 `mx.set_default_device(mx.gpu)`，在 GPU stream 执行 MLX 数值操作，再建立模型/数组；Torch 明确 CPU，intra/inter-op 各最多 2 线程。设备证据记录实际 default/stream 与 Torch device，DLPack 仅记录硬件互操作标签。CPU 默认入口不得静默转 GPU。

复用已有 P01 replay 环境，只读核对 MLX 0.32.2、MLX-LM 0.31.3、Torch 2.14.0、NumPy 2.5.2、psutil 7.2.2，以及配置中的 trainer/datasets 原件 hash。保持原生 `train`、`evaluate`、`TrainingArgs`、`iterate_batches`、`loss` 注入点和上游 compile。不得复制上游训练循环、伪造 device metadata、monkeypatch 数值结果或关闭 compile 来取得通过。

既有 `preserve_wired_limit` 可在独立 leased 进程中原样复用，仅记录并抑制上游 OS wired-limit setter 请求；必须恢复原 API 对象，保留事件和恢复证据。不得改这个 P01 模块或其他系统/allocator 限制。

## 必须实际完成的数值验收

1. 原创 13 例逐例核对 MLX GPU 与独立 Torch CPU 的 CE、有效分母、完整梯度数组；float32 绝对容差固定 2e-6。保存原数组与参考，验证 shift、completion/EOS 监督、右 padding 的 loss/梯度不变，以及改变被忽略预测位置 logits 不改变 loss。保留并复现上游 default_loss 多监督 padding 的反例。
2. 使用同一 model/optimizer/RNG 对象，seed 42、SGD lr 0.07、无 momentum/weight decay。真实原生分段 train 按 8+5 微步完成两次更新，原顺序每例恰好一次，等权平均每例 completion-token-mean CE 的梯度，尾段真实除 5。逐个实际 checkpoint 参数与 Torch 的两个更新状态比较；不仅检查计数或 mock。
3. 另一个干净、有限运行使用同样 13 例和上游单段 accumulation=8，实测其只更新一次、遗失 5 个尾微步；与完整两次更新参考的差异必须真实保存。这是 expected negative，不把进程成功捕获反例写成训练正确。
4. 每个分段保存后的实际状态调用 native evaluate，完整遍历同一 13 例一次，validation 使用总 CE/总有效监督 token。绑定实际参数内容 hash、checkpoint 文件 hash、固定输入/validation 身份、optimizer step 和 processed microsteps。尾更新后重新评估并实际保存重载，核对重载参数/得分，拒绝将第一个 checkpoint 绑定到第二次更新参数；独立 Torch token-weighted validation 比较在相同容差内。该验证集仅用于状态记账，不是泛化/模型质量测量。
5. 对实际两状态运行既定 score 选择规则，并记录被选 checkpoint 的真实身份；CPU/GPU scope 不混选，未授权 formal/未知 scope、错误配置、错误或非当前租约、变更输入、空分母、超界参数/样本/序列及已有输出目录均失败。入口守卫的 CPU 测试与实际框架数值运行分别计数。

## 资源与失败终态

单个独立自有子进程在任何框架导入/数组前实际取得同一个 `gpu0` OS 租约，并持有至进程真正退出；元数据空闲不是启动许可。每次 wall≤300 秒、RSS≤4 GiB、实际 MLX peak memory≤1 GiB，每个 backend 最多 2 次更新；硬上限仍为13例/16 token/词表16/4096元素，实际固定输入更小。保留同步后时间、RSS 采样和 MLX 内存原值，不能把这套 toy 速度外推真实模型。

本轮 T1 总共最多 5 次 framework 子进程启动，失败也计数；预期为源码 segmented、源码 unsegmented negative、安装版 segmented 三次，余两次仅供真实失败后的修正。成功路径不无差异重复。每次启动前登记模式/源码/预算，在独立新目录保存；超限或异常后仅终止回收本轮自有进程，保留真实 exit/失败/stdout/stderr、wait/reap、PID 不存在及租约释放证据。预算耗尽或无法通过上游公开接口时交 S0，不提高限额、不自建训练框架。R1 或 S0 的新 framework replay 必须有后续独立明确范围，不能借此共用 T1 的额度。

不加载 Qwen/任何预训练权重，不优化真实 P02 数据，不开展真实 baseline/生成/容量/SFT/DPO，不新建环境或下载依赖/权重，不启动网络 tracker/服务、费用或上传。原 `training_authorized=false` 和全部人工门槛保持。

## 测试、打包与交接

在精确候选运行新边界和现有完整 CPU 组：当前组合895/2，另格式60、截止时间2、训练绑定13（110 subtests另记）、原SFT独立44，共1014 passed/2 HF-only skips。这是基线，不是本轮预先通过的结果。保留原收集与断言，新测试、重复检查和数值运行分开计数；完成适用 Ruff、4契约冻结、公开扫描与diff检查。

实际新构建 sdist、默认 wheel 与显式 sdist 重建 wheel，逐成员对 Git、metadata、entry points、license 和完整 RECORD。用现有默认环境的新 target 离线 `--no-deps` 安装，非源码 cwd 验证默认 CPU prepare/帮助/拒绝路径、全部模块实际 origins 和无可选框架导入。再用现有 replay 环境与新的安装 target 运行一次上述 bounded installed segmented，确保新增 native 模块及两份变更模块实际来自 wheel、无源码路径回退；此数值运行计入五次限额。普通源码直接 wheel 未运行则如实 NOT_RUN。

交付完整 candidate/parents/tree/所有权 diff、精确授权与配置 hash、源码及实际命令 epoch、原始 argv/cwd/环境/UTC/退出码/完整日志 hash、三份归档/安装版 origins、全部数值状态与资源清理、旧 P01/P04 refs/制品保全。公开只原创代码和去敏统计/hash；完整数组、绝对路径、任务ID及日志私有保存。原样普通推送新分支，提交 handoff 后结束本轮，等待独立 R1 与 S0；不得把自测写成整包已验收或继续领取正式 P04。


18:21:46–18:21:49 UTC，S0直接核验新branch/HEAD/原生身份、11份授权副本、精确配置/固定cases、401份基线当前字节与1559份原私有制品，共1976当前路径通过；已有环境的五个版本及trainer/datasets原件hash以metadata只读核对，无S0框架导入/数值replay。证明SHA-256为7158cd8cddf70f3cf45df0c461d3e2518ff21c51f762faf0f647398f993b46e7。intake已验收，T1继续同一授权；实现、数值和独立R1验收仍待完成。

18:49–18:57 UTC中间核验：S0已核对534445b的两次原GPU运行：13例完整数值、8+5实际更新/两个checkpoint及原单段丢尾反例通过；fae3d60监督器终态缺陷的CPU定点回归通过。完整候选/安装版独立核验、R1、最终CI/main仍待完成；人工与正式P04门槛保持。原数值证明563a3e83a6682f33a2b869833d15aaca4a03310241cb3e26fa0b82fcfffcd9d1，监督器定点回归证明d387826e624d5c44724481eacbbab9de24d32ffe8a280e572d0a95836fa6d314；见[S0报告](../../reports/S0_P04_SFT_NATIVE_TOY_INTERMEDIATE.md)。原配置与五次T1框架限额保持。

完整交接已核验：候选f7326d1，parent c06782a、tree247eba0，原生终态19:20:31 UTC。S0交接证明b3b3e5b54abcc451f76e8731d72e00b516373b2f3f297abcacfabc0a48082f26，见[报告](../../reports/S0_P04_SFT_NATIVE_TOY_HANDOFF.md)。T1本轮结束，未用额度不转授；[R1独立范围](P04_SFT_NATIVE_TOY_REVIEW.md)READY未派发，正式P04门槛保持。
