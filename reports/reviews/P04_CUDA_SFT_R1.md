# P04 CUDA SFT：R1 独立技术审查

**PASS；P0=0、P1=0、P2=0。** Reviewed candidate：`4342af87615197c7947d001f462d3d31500cd501`；代码/测试提交：`95cf14224ceb2ea3a3e817826aeef0e651eb459d`；差异基线：`61c2176d556fd0e4cfc2af00b16242dddcfadfd3`。授权：`6ed2f020f923a8faafc21d4175ca5750aaaa5b23`，最终候选由 S1 同轮追加提供。审查日期：2026-10-26（UTC+8）。

该 CPU 实现可以进入 S1 的真实数组验证和后续 Colab 集成验收。本结论覆盖最终 SIGTERM 修订；真实数据 prepare/新编码、真实模型加载、CUDA 容量与跨实例恢复仍待各自实测。E1 控制包的既有独立 FAIL 不由本审查关闭。

## 主要核验结果

- **损失与优化正确。** 训练消费已经 shift 一次的 `Batch`，forward 不传 HF `labels`；只监督 completion 和单 EOS，忽略 prompt 与右 padding。每个样本先取监督 token mean，再按实际累积组长平均。独立四参数模型核对了末组 7/2 的两次 AdamW 更新、bias correction、moments 与固定 LR；底座参数保持不变。验证按全序列总 CE / 总监督 token 聚合。
- **LoRA 接口符合冻结配置。** 源码限定 Q/V、28 层、56 模块、rank 8、alpha 16、`use_rslora=False`、dropout 0，检查实际模块集合、trainable 数量和 dtype。官方 PEFT 的原创微型 Qwen CPU 测试通过：BF16 底座、FP32 adapter、SDPA、关闭 cache、non-reentrant checkpointing，adapter 更新且 frozen weights 不变。真实 0.6B/1.7B 的参数与显存检查尚未运行。
- **恢复与选择通过 CPU 验证。** 原创 32 参数模型连续 3 步，与新进程从第 2 步恢复后的第 3 步，逐样本 loss、adapter hash、Python/NumPy/Torch CPU RNG hash 完全一致。缺失 Adam moments、身份/游标/score 不符和损坏 RNG 被拒绝。checkpoint 的固定 LR、完整 optimizer、游标、RNG、源码/配置/数组/模型/依赖身份均有明确绑定；反序列化使用 `weights_only=True`。
- **保留规则通过。** 本地和第二副本的完整文件均读回核对。三个已评分状态中，分数并列选择更早的第 1 步，保留 best=1、rollback=2、last=3；连续和恢复轨迹的第 3 步成为新 best 时，两份目录均保留第 2、3 步。历史 best 随完整 checkpoint 携带；旧 run 的其余保留状态仍属于旧 run 制品。
- **退出清理通过实际进程检查。** 最终 `supervise` 的外部 SIGTERM、内部 deadline、正常完成三个用例均通过，独立 session 中的自有 child 已退出，随后只读回查仍不存在，原 SIGTERM handler 恢复。测试 actor 捕获外部终止产生的 `SystemExit(143)` 后正常退出；没有把 actor 的 exit 0 写成训练入口的退出码。代码还处理 spawn 登记 PID 前收到 TERM 的延迟清理，并在清理期间忽略重复 TERM。
- **数据与执行边界符合 CPU 首包范围。** 检查了四个冻结 view、cohort/原行/audit、tokenizer/model revision、生成源码和 portable 文件摘要的绑定，以及一次 shift、EOS、mask、split/order/coverage 拒绝路径。真实数组身份仍需 S1 对实际产物核验。真实 loader 先取得共享 `GPULease`；缺少 CUDA/BF16 明确失败。原创锁测试在独立临时 Git 仓库中验证重复租约拒绝，没有占用实际训练租约。

## 独立数值证据

R1 原创模型只有一个可训练标量和三个冻结参数，序列 bucket=8，每条优化轨迹 2 updates。取初始标量 `theta=ln(2)`，三类 logits 为 `[x*theta, 0, 0]`，根据手工指定的源 token，`x` 为 1 或 2。参考值由明确的目标计数和标量公式计算，不调用生产 CE 或 autograd 计算 oracle。

| 检查 | 独立参考 | 实际结果 |
|---|---:|---:|
| 短样本 CE sum，2 个监督 token | `ln(6)` = 1.791759469228055 | 1.7917594909667969 |
| 短样本 mean-loss 梯度 | `-1/12` | -0.08333331346511841 |
| 长样本 CE sum，4 个监督 token | `ln(216)` = 5.375278407684165 | 5.375278472900391 |
| 长样本 mean-loss 梯度 | `5/8` | 0.625 |
| 验证 token mean | 1.1945063128187032 | 1.194506327311198 |
| 两样本等权训练 mean | 1.1198496682675345 | 1.119849681854248 |
| 末组 7，第二步 theta | 0.6929471813251715 | 0.6929471492767334 |
| 末组 2，第二步 theta | 0.6929471811930493 | 0.6929471492767334 |

CE sum 绝对容差 `5e-7`，梯度/loss/参数 `2e-7`；Adam 一阶 moment `2e-8`、二阶 moment `1e-10`。全部通过。训练等权与验证 token 加权的预期差为约 0.07466，检查可区分两种聚合。首次脚本因自定义 toy profile 未在既有验证器注册而退出，尚未执行 optimizer updates；只把 profile 名称改为既有 `TOY_CPU` 后通过，数值断言与生产代码没有修改。

## 实际命令与来源

使用 S1 已提供的 Python 3.12 CPU 环境，`PYTHONPATH` 指向 R1 自己的 `src`；HF/Transformers offline，OMP/MKL 各 2。没有新建环境或安装依赖。下表用 `CPU_PYTHON` 表示该现存解释器；完整绝对 argv、UTC、PID、stdout/stderr 和退出码保存在本轮私有命令回执。

| 命令或检查 | 实际时点与结果 |
|---|---|
| `CPU_PYTHON -B -m pytest -q tests/training/test_cuda_sft_protocol.py tests/training/test_cuda_sft_tensors.py --basetemp=NEW_CORE_TEMP` | 核心 `6392f3c`：14 passed，13.40s，exit 0 |
| `CPU_PYTHON -B -m pytest -q tests/training/test_cuda_sft_process.py --basetemp=NEW_PROCESS_TEMP` | 最终 `4342af8`：3 passed，3.18s，exit 0 |
| `CPU_PYTHON -B independent_numeric_v2.py` | 最终 `4342af8`：独立 CE/梯度、验证权重、末组 7/2 两步 AdamW，exit 0 |
| `CPU_PYTHON -B audit_v2.py` | 最终 `4342af8`：73 包文件、31 份作者记录、两份实际锁、恢复/保留制品与三个 child 终态，exit 0；未导入框架 |
| `python -B -m ruff check src/toolalign/training/cuda_sft tests/training/test_cuda_sft_process.py tests/training/test_cuda_sft_protocol.py tests/training/test_cuda_sft_tensors.py` | 现存 lint 环境：PASS，exit 0 |

14 项与 3 项分别使用新的独占 basetemp。已核对核心到最终提交只有 `supervise` 清理及新增进程测试的代码差异；核心的 engine、arrays、checkpoint、protocol 和原两份测试逐字不变。对全部最终差异独立阅读并实跑新增路径后，不重复未变的 14 项。旧 163 项与 S1 既有数据准备证据沿用。

E1 精确 `8faa75e7010290a11f13a8006fba5d4b16ac44f9` 的 Linux hashed lock 48 pins 解析通过；Mac lock 37 pins 与共享环境实际安装版本逐项相符。此项只核对依赖接口。作者 `pytest-07` 的 11 个配置/源码/测试摘要均与最终候选一致；原 `pytest-06` 的 runtime 摘要绑定核心提交，其 SIGTERM 泄漏失败记录保留。

R1 私有原始证据保留全部成功与失败：

- `independent-numeric` 首次 exit 1：审查 fixture 的 profile 名称不合法；原脚本与原 traceback 保留。
- `final-audit` 首次 exit 1：把 pytest 的 `current` 符号链接重复计为第四个进程用例；只读索引器改为不重复计别名，原索引器与原回执保留，没有重跑数值或进程测试。
- 作者原 FP32 容差、空 Adam moments、SIGTERM 及初稿静态检查失败的记录保持；本次最终候选的正式裁定仅一次。

关键私有证据摘要：独立数值脚本 `dc3a5409e1d4b2a3ee972e09131d5e695aa6903d003ea0feb5c9ab3285d9e3c4`；数值结果 `d764f3400bbcc347f1d933683e54f4147ee5448f478d1405f733c7cf5b0ffb87`；绑定审计结果 `23511dd01bb1208c5bd360817bc84ff74a7152eb68dfe078bfa0134eef6b7c22`。原命令、作者记录副本与测试制品索引由 S1 从本机交接读取，未提交私有路径、数据或模型文件。

## 后续验收

本轮真实 prepare/新编码、真实模型加载/下载、GPU/SSH/训练均为 0。下一步由 S1 集成已审代码，完成冻结 20 例的实际 portable arrays 与 Q1 对应核验，再在 E1 控制修订通过后执行有界 Colab 容量、完整制品回收与新实例恢复。CPU toy 和第二目录读回不替代真实模型、外部持久化或跨实例恢复验收。
