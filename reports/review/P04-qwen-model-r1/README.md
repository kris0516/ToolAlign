# P04-QWEN-MODEL-R1 独立 CPU 审查

**PASS；P0=0、P1=0、P2=0。** 结论仅适用于完整候选 `01eeb74d1bce3c3a3c41d84575d4d706e246e818` 的固定 Qwen 文件、接口与 CPU 技术边界。真实模型加载、实际 LoRA 装配/重载、forward、优化、生成与容量均为 **NOT_RUN**；仍需 S0 整合、最终 CI/main 验证和后续独立运行授权。

审查者为独立 R1 AI 对话，`gpt-6-astra/max`；沿用隔离 worktree 和新分支 `codex/review-p04-qwen-model-r1`。candidate tree 为 `3b194325c9b6ecba4356f46eb4ad91c8f9e63642`，源码 checkpoint 为 `207c24c486a562760c51b8de3193c3e78028ba6d`，生产基线为 `a2b595c39d84f4e3ba32ee5893f3fff8c9202f4d`，完整授权为 `9a29a72f9c418ff5c18c12f0065eae4f311aa3ec`。契约为 plan-v0.1、toolalign.contracts.v1、角色保留 Action JSON v1 与 ADR-0027。review 提交直接以完整 candidate 为唯一 parent，仅新增本审查目录和对应 handoff。

## 结论依据

完整 diff 为六个获授权的新文件：固定 metadata、生产模块、相关测试、两份实验报告和 E1 handoff。617 份生产基线文件及 623 份候选文件逐项绑定；R1 未修改候选代码、测试、配置、依赖、CI 或协调看板。13 份授权文档及实际授权 PROJECT_STATUS 已封存。

42 项固定输入（13 份小文件副本、20 份原模型文件、9 份库 metadata）、E1 的 34 条原始命令和 20,862 份源码时点、三份实际归档及原安装目录已独立核对。intake 共验证 23,838 条文件路径。来源证明中另有 3,142 条旧数据/构建出处路径，仅绑定其证明，不扩大读取范围。固定配置 SHA256 为 `b8a5e48bc2b93064c511ba796dabf55024f65df97fe0db39c43366b7bc877145`，manifest SHA256 为 `41aadaa79eac7467c7ef2b7c39a0524ec894d1b0e9c616d7a6ab303d05e33cc5`。

| 审查边界 | 独立证据与判断 |
|---|---|
| 固定文件与解析顺序 | 固定 metadata hash、model ID/revision、文件集合先校验；所有声明文件 hash 先于 JSON/header 解释。核对三个原 header、全 622 个序列化 tensor 的名称、BF16、shape、连续 offsets/payload 和分片 index。重复键、重复 tensor、非有限 JSON、bool/float 整数替代、额外 model 文件、自定义架构和量化覆盖有 CPU 拒绝用例。 |
| 普通文件与路径 | 每层目录使用 directory FD、`O_NOFOLLOW`，最终文件使用 `O_NONBLOCK` 并在同一 FD 上 `fstat`。新增 6 个有界 child，分别在 hash/read/header 的实际 open 前替换成无 writer FIFO 或 symlink，均及时拒绝；第 7 个 child 在父目录 FD 已打开后替换父目录，仍只读到原 FD 指向的原文件，后续目录复核拒绝替换后的路径。所有 child 回收。 |
| 完整参数集合 | 依据已固定 Qwen3 constructor、sanitize 和 LoRALinear 源码，独立推导两个模型的全部名称/shape，并与 intake 已核对的 header 对应。311 个序列化 BF16 叶仅移除 `lm_head.weight` 后为 310 叶；绑定 embedding/head 的 shape、dtype、固定原字节 hash。28 层 q/v 共 56 个模块，112 个 FP32 A/B，逐项核对底座改名与 rank8/scale2/dropout0。 |
| 真实加载门 | 先验证调用方当前物理 gpu0 租约的 common-dir、FD/inode、PID/start/host/metadata，再验证文件、版本、固定源码和导入来源；只向固定本地 `load_model` 传入 `lazy=False, strict=True`。上游源码显示 strict eager 权重加载并覆盖双 EOS，无 Hub/tokenizer 调用。原租约由调用方持有至全部模型引用释放。本轮只验证源码、CPU 拒绝和模拟编排。 |
| 参数原始身份 | 逐叶绑定完整 name/shape/dtype/原始字节；`view(uint8)` 的固定上游说明保证二进制表示，未采用 BF16→FP32 后的 hash。原始 BF16 signed-zero/NaN payload 模拟、FP32 非有限/shape/内容拒绝通过，宿主复制实测模拟边界为 1 MiB 加最终 6 字节。检查器也验证 trainable 集合和对象对应关系。 |
| 固定 LoRA 与重载 | 源码和模拟检查固定模块的精确类、A/B/底座对象、scale/dropout；装配前冻结底座，初始 B 为零。重载先验证显式 adapter 文件 hash、完整 keys、dtype/shape，再核对已加载叶的原字节与有限性，以 `update(..., strict=True)` 更新固定 A/B，最后复核实际全部 A/B 和全部冻结底座。上游 strict update 允许局部参数，因此完整集合/内容复核必需；本实现具备这些复核。失败 wrapper 进入终态并保留首个异常。 |
| 包与默认环境 | 两个 wheel 各 70 成员，内容一致；sdist 144 文件与候选/metadata 对应，源码、LICENSE、entry points、RECORD 均核对。一次离线 `--no-deps` 安装后，从 checkout 之外以 `-B -I -S` 验证 65 包文件、69 个未改 wheel 成员、75 条安装 RECORD 和 9 个 ToolAlign 导入来源。无租约 load 在模型文件读取和框架导入前拒绝。 |
| 执行授权 | metadata 的 `is_run_authorization=false` 保持。原 sampling 默认 `do_sample=true`、temperature/top-k/top-p 只作为原文件身份；未改成后续 greedy 配置。生成双 EOS 为 151645/151643，训练 EOS 为 151645，pad 为 151643。模块没有训练、生成、评分或 checkpoint 选择。 |

## 实际验证

- 现有相关 CPU suite：`pytest -q tests/model_io/test_qwen_model.py`，**120 passed**。
- [R1 原创探针](test_independent.py)：**14 passed**，包括 7 个文件替换 child、2 个完整模型名称/shape 推导、5 个原始字节模拟检查。没有把 E1 的重复执行次数累加到此计数。测试使用两个独占 basetemp；现有 suite 观察到 90 个 subprocess 和 1 个 fork，原创探针观察到 7 个 subprocess，均回收。
- `ruff check --no-cache .`、契约冻结、公开内容扫描和 `git diff --check` 均通过。原始命令、UTC、exit、stdout/stderr、源码与 consumer 时点保留于私有证据；[公开验证索引](verification.json)提供 hash 与适用范围。
- 安装版 `validate_model_files` 严格先落独占 reservation，每模型各调用一次，共一轮两次；0.6B 的 9 文件、1.7B 的 11 文件全部通过。计数由实际函数调用观察，框架/真实 tokenizer/tensor 解码/模型/GPU 均 0。新增安装和实物 API 剩余额度均 0，不重复运行。

| 固定模型 | revision | 序列化叶/参数 | sanitize 后预期底座叶/参数 | 预期 LoRA 叶/参数 |
|---|---|---|---|---|
| Qwen/Qwen3-0.6B | `c1899de289a04d12100db370d81485cdf75e47ca` | 311 / 751,632,384 | 310 / 596,049,920 | 112 / 1,146,880 |
| Qwen/Qwen3-1.7B | `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` | 311 / 2,031,739,904 | 310 / 1,720,574,976 | 112 / 1,605,632 |

以上运行时参数数量是固定源码/header 推导，未实例化真实模型。每叶原始字节 hash 作为 S0 固定输入保留；R1 独立验证原文件整体字节、header 和完整名称/shape，不把这些证据写成真实驻留参数 hash 已测通过。

## 原失败与证据保全

E1 的 `006-ruff-new`（unused import）和 `007-pytest-origin-state`（错误前缀断言）原失败、输出和源码时点保留；完整候选的相关检查通过。34 条原命令已逐项匹配原生实际 invocation、argv、completion、exit 和 recorder 输出，不只信任自述结果。

R1 的 `native-audit` 首次失败来自审查辅助脚本：003 的实际 shell 先打印两段源码和 wc，再运行 recorder。修正辅助脚本对已观察前缀的处理后，`native-audit-r2` 对 34 条实际命令和 recorder 输出全部精确绑定。另一次只读控制台展示脚本对 dict 使用 slice 导致 KeyError，原生输出保留；二者均未修改候选或消费实物 API，未冒充产品缺陷，也未删除失败。

切换前独立核对原数据审查 `b99a644e3ac0386f5ebe55cfd32e51b99e89781a` 的 65,186 份文件、1,628 个不跟随的 symlink、1 个仅 lstat 的 FIFO、623 份公开 Git/冻结副本和 1,189 条更早 Git 绑定。原 30 个临时文件路径及 1 个链接仍按“原路径缺失、有原等价字节/封存副本”继承，不恢复为原件。原 FAIL/PASS、旧问题 counter、根身份、原私有提交与证据保持；本范围不关闭其他包的问题。切换后的旧公开字节按原 Git/冻结副本绑定。最终私有 seal 和原生 S0 handoff 绑定 review commit、发布检查及新旧证据。

新增归档构建、依赖/环境、模型下载、大权重副本、数据 build/数组、真实框架/模型/训练/生成、费用、模型/数据上传和公网服务均 0。本报告的 PASS 不授予这些运行权限。
