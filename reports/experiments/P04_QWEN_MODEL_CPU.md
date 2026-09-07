# P04 固定 Qwen 模型接口：CPU 交付

**READY_FOR_REVIEW。** 新增固定本地文件验证、延迟 loader、LoRA 与 adapter 参数身份接口；120 项原创 CPU／物理锁／明确模拟对象测试通过，源代码和安装版各一轮真实文件字节及 header 核验通过。真实模型加载、MLX／LoRA 装配、参数内容测量、adapter 重载、forward／优化／生成均 **NOT_RUN**。本报告不授予模型运行或正式训练许可。

E1，`P04-QWEN-MODEL-CPU`；基线 `a2b595c39d84f4e3ba32ee5893f3fff8c9202f4d`，完整授权 `427e5e8fb49a4719afd5e09b53c2d012c52e7e80`，同轮构建支持 `97ca7091c239f5fbfbdbde2db401eb72532bb38a`。源码提交 `207c24c486a562760c51b8de3193c3e78028ba6d`，直接以基线为父；最终文档提交不改变包源码。契约为 `plan-v0.1 / coordination.v1 / toolalign.contracts.v1`，按 ADR-0027。结构化证据见 [JSON 对应件](P04_QWEN_MODEL_CPU.json)。

## 接口与固定行为

生产新增仅 [qwen_model.py](../../src/toolalign/model_io/qwen_model.py)，测试为 [test_qwen_model.py](../../tests/model_io/test_qwen_model.py)。唯一配置新增是 S0 的 [qwen-models.v1.json](../../configs/qwen-models.v1.json) 原始 372,437 bytes，SHA `b8a5e48bc2b93064c511ba796dabf55024f65df97fe0db39c43366b7bc877145`。旧 model_io、默认 CLI、训练/toy、P03、契约、依赖、构建和协调文件保持基线字节。

| 入口 | 行为与边界 |
|---|---|
| `validate_model_files(model_root, *, model_id, revision, config_path)` | 先核对固定配置原字节；校验全部 9/11 文件，再解释 JSON/header。显式绝对本地路径，逐级拒绝符号链接，拒绝额外权重、重复 tensor、错误分片/offset/类型/shape/hash，以及模型配置覆盖 |
| `require_current_lease(lease, repository)` | 核对已有同 Git common directory 的 gpu0 文件、真实 inode/描述符、PID/启动时间/host/运行身份及物理锁。调用方提供可信 ToolAlign checkout；目录或非空句柄本身不足以证明持锁 |
| `load_qwen_model(..., lease, repository)` | 租约、文件、现有库 METADATA、9 份关键源码与导入来源核验后，才进入 MLX import 和固定本地 `load_model(lazy=False, strict=True)`。不创建 tokenizer，不提供架构/量化/验证跳过参数 |
| `QwenModel.model / parameter_identity()` | 返回对象绑定原租约与实际 module origin。参数检查按实际对象键、shape、dtype、原内容核对，失败状态不可继续；调用方负责模型全部引用销毁前持续持租约 |
| `attach_lora()` | freeze 后装配全 28 层 q/v，rank 8、直接 scale 2、dropout 0；检查固定模块、112 个 FP32 A/B、初始零 B、仅 A/B 可训练和 BF16 底座不变 |
| `reload_adapter(path, expected_sha256=...)` | 已有同配置 LoRA 结构上，先核对文件 SHA、精确键/shape/F32 和全部内容；只通过严格部分更新写入 A/B，随后重核实际 A/B 与全部冻结底座。checkpoint 选择/写入不在本包 |

参数原字节使用 MLX 的位表示 `view(uint8)`，按 C-order、小端读取；每次宿主复制最多 1 MiB，不将 BF16 转 FP32。按叶计算 SHA256，名称、shape、dtype、字节数与叶 SHA 再以排序 UTF-8 JSON 绑定。叶级 device reshape 可能物化单个叶；真实内存/时延仍待后续运行测量。基础权重始终对照 S0 safetensors 原字节 hash；LoRA 的 56 个底座名映射至 `.linear.weight`，其余保持。

库验证固定现有安装位置/版本/METADATA与关键源码，检查加载前/后的 module origin，并拒绝 Python 文件冒充 `mlx.core` 扩展。它是当前进程的协作边界，不是对任意恶意 Python 代码的沙箱。文件和目录身份在重要操作前后复核；模型根必须保持只读，检查点应位于独立输出目录。

## 已验证的静态事实

| 模型 | 原文件 | BF16 header tensor | sanitize 后预期底座叶 / 元素 | 预期 LoRA A/B / 元素 |
|---|---:|---:|---:|---:|
| Qwen3-0.6B，revision `c1899de289a04d12100db370d81485cdf75e47ca` | 9 | 311 | 310 / 596,049,920 | 112 / 1,146,880 |
| Qwen3-1.7B，revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` | 11 | 311 | 310 / 1,720,574,976 | 112 / 1,605,632 |

实际 header 计数与源码推导的运行计数分别登记。原独立 `lm_head.weight` 与 embedding 的形状、dtype 和原内容 hash 一致；固定 sanitize 仅移除 head，未来真实装配必须再次验证实际 310 个底座叶。原 generation config 的 EOS 为 `[151645,151643]`，训练 EOS 151645、pad 151643；`do_sample=true / temperature=0.6 / top_k=20 / top_p=0.95` 保留为原文件事实，不是本包执行了采样或制定了 greedy 策略。

## CPU 与安装证据

所有时间均为 UTC。19:03:37–38 最终新测试 **120 passed、0 failed、0 skipped**；执行时为基线加新文件，逐字对应随后 `207c24c486a562760c51b8de3193c3e78028ba6d`，不是提交后额外重跑。先前 77、107 和 117+1 的运行保留，不累计为独立测试数。用例覆盖重复/非有限/UTF-8 JSON、bool/float 数值换型、路径和分片边界、物理 flock/当前 PID/host/fork、导入来源、BF16 原位表示、LoRA 结构/冻结/有限数、adapter 预检查及更新后污染。miniature spec 与模拟对象明确 `MOCK_ONLY`，未放宽公开配置常量使其成为真实 Qwen。

源代码允许的一轮在 19:07:51–53 完成，安装版一轮在 19:12:42–44 完成；每轮两模型／20 原文件／622 header，完整权重文件流式 hash、0 tensor 值解码。两独立解释器安装了禁止框架、tokenizer、Hub 导入的观察守卫，实际尝试均 0。源证据 SHA `21512c5f0787b23a86c1f76c43f9c561717c0fb4869b6e53f9c4d90619d94ffd`，安装证据 SHA `c4416f988c27a205dfc0279d0e293d8200a2893b9f1d5eddc2d8613277a319a2`。初始 intake 对 42 固定成员的 hash 是单独要求的接收核验，不冒充另一轮模型 header 验证。

复用 S0 已确认的现存 Python 3.14.7 / Hatchling 1.27.0，实际构建 sdist、直接 wheel、从该 sdist 重建 wheel。以现存 uv 0.12.5 `--offline --no-deps --no-cache` 安装新默认 target；没有创建环境、下载或安装新依赖。`-B` 与 `PYTHONDONTWRITEBYTECODE=1` 保持；196 份既有构建支持字节复核通过。

| 实际归档 | bytes | SHA256 |
|---|---:|---|
| sdist | 401,044 | `73ee4795ca39d81021b3eed1eb1ed4b8a9e9d3caf5899469e91cfd75f5f7e1cf` |
| direct wheel | 204,275 | `117f74f92aad166aceb16336771ec4d4bf9f98e7ac6142fb0592d2c1246373d6` |
| rebuilt wheel | 204,275 | `117f74f92aad166aceb16336771ec4d4bf9f98e7ac6142fb0592d2c1246373d6` |

144 份 sdist 成员中 143 份绑定原 Git 内容，另 1 份为生成的 PKG-INFO；两个 wheel 的 65 个包文件和实际 target 字节均与源码一致。新配置/测试在 sdist，新生产模块在两个 wheel。非源码 cwd 下全部 ToolAlign import 均来自新 target，纯导入、4 个错误输入/无租约拒绝场景和固定文件验证通过。归档/安装绑定证明 SHA `f5c4dbd69e3332f30dae50ad372d114ee70a88822a083818be95028dc22e46ce`；不把这些结果写成真实 loader 运行通过。

全库 Ruff、4 个冻结契约、源码阶段 620 路径公开扫描及 diff 检查通过。最终文档的公开检查与候选/命令/全部输出/源码时点/实际三归档和安装来源由最终交接 seal 绑定。旧 HF/数据构建/原生 toy 数值未追加重跑。

## 保全、失败与后续

14 原授权副本、2 同轮补充、617 基线文件、42 输入（13 精确副本／748,369 bytes，29 引用）保持；intake receipt 包含 4,135 文件，receipt 自身另计 1，S0 接收证明核对 4,266 路径。新身份只写新 scope。19:16:19 的再次保全核对 4,376 当前路径：原 da22baf 的 498 个公开 Git/快照、1,209 旧 scope 文件、39 链接、旧 refs 与根 identity 保持。授权 checkout 改变的旧公开位置按原 Git/快照绑定，不宣称当前 checkout 仍是 da22 字节。保全证明 SHA `da29eaddd36f45cb45e760748153cec1a0f98af48f9492ce1ebbe6485a45ee1c`。

保留本轮两条辅助非零：Ruff 的测试未使用 import；新增来源反例的错误消息前缀预期不符（生产正确先拒绝文件大小）。修正测试/补齐用例后通过，原 stdout/stderr/源码快照保持。早期只读探索另有不存在的候选 lease 路径及原生工具参数上限错误，未产生生产修改或模型运行。

本轮前四次 pytest 使用默认共享临时根。S0 随后报告另一旧临时 fixture 缺失并核查归属与替代封存；本包不猜测清理原因，也不将该目录写成保全通过。新要求为后续 pytest 显式采用新建、独占且不处于 `.toolalign-local` 祖先下的 `--basetemp`；收到通知后没有重跑成功测试或恢复/清理旧临时目录。

状态为实现者 CPU 自查通过、**待独立 R1**；新包最终 CI/main 由 S0 处理。后续真实运行须另有 S0 任务/精确配置与原物理租约，验证实际加载、零 LoRA 对照、容量、参数变化、保存重载及实验结果。metadata 的 `is_run_authorization=false` 表示其不是运行许可，不能改写成许可或解释成永久禁用未来合法 loader。正式训练、评测、模型服务、公网接口和模型/数据上传均未发生。
