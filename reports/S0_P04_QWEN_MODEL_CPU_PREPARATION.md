# S0｜固定 Qwen 模型接口 CPU 准备

状态：**CLAIMED，输入已冻结，尚未原生派发**。任务 [P04-QWEN-MODEL-CPU](../coordination/tasks/P04_QWEN_MODEL_CPU.md)由原独立 E1 承接，gpt-6-astra/max；代码基线 `a2b595c39d84f4e3ba32ee5893f3fff8c9202f4d` 的生产源码保持已验证 PR15 main90c4da9。本包新增固定文件验证、延迟 loader 和参数/LoRA 身份接口，供后续训练与推理复用；与 T1 当前数据 CPU 适配使用独立模块和 worktree。两包各自完成独立审查及 main 验证后，再冻结真实运行范围。

S0 于 2026-09-07 18:04:24 UTC 只读核对两模型 20 个现有文件、9 份环境 metadata 和固定源码，35 路径证明 `8effb47b0123e9510820393733ea90b5cfd5260d045d5fd2114afbb07e75a0e5`。通过 stdlib 读取 safetensors header 并流式 hash 原 tensor 字节，未构造数组或反序列化 tensor 值；固定源码表明 tied-embedding loader 移除独立 `lm_head.weight`，LoRA 将 56 个底座权重名映射至 `.linear.weight`。实际加载及参数装配仍 NOT_RUN。

| 项目 | Qwen3-0.6B | Qwen3-1.7B |
|---|---:|---:|
| 实际文件 header 中 BF16 tensor 数 | 311 | 311 |
| 实际序列化元素数（含独立 head） | 751,632,384 | 2,031,739,904 |
| 按固定 sanitize 推导的底座元素数 | 596,049,920 | 1,720,574,976 |
| 按源码推导的底座参数叶数 | 310 | 310 |
| rank 8、q/v、全28层 LoRA 的预期元素数 | 1,146,880 | 1,605,632 |
| 预期 A/B tensor 数 / 装配后总叶数 | 112 / 422 | 112 / 422 |

两份原 `lm_head.weight` 与各自 embedding 的 shape/dtype/原字节 hash 一致。这些是原文件与源码推导，不能当成实际运行对象的检查结果。实际 model generation config 均声明 EOS `[151645,151643]`，训练 EOS 151645、pad 151643；原 sampling 默认值原样保留，后续 greedy 设置独立登记。

[固定模型 metadata](../configs/qwen-models.v1.json) SHA `b8a5e48bc2b93064c511ba796dabf55024f65df97fe0db39c43366b7bc877145`，372,437 bytes。它包含准确文件/header/参数映射与固定源码身份，`is_run_authorization=false`，不能自行作为模型运行许可。原静态绑定 `a3bd3a03` 和原本地文件接收 `c44fdf17` 保留；新文件补齐了 5 份 MLX 支持源码的 hash，不修改旧文件或原模型。

18:17:20 UTC 完成 E1 输入冻结：manifest `41aadaa79eac7467c7ef2b7c39a0524ec894d1b0e9c616d7a6ab303d05e33cc5`，42 成员，13 精确 metadata/源码副本合计 748,369 bytes，29 只读引用为两模型的 20 文件及 9 环境 metadata。没有复制权重；绝对路径仅在私有输入。出处/proof 内其他路径不扩大读取范围，E1 不读取 P02 内容或 T1 变化中的实现。

E1 原 da22baf 类型修订已 completed/notLoaded、分支干净。S0 复核原接收 2,943 路径、498 原公开 Git/新快照、1,209 当前旧 scope 文件、39 链接文本、原 refs 和根 identity，保全证明 `61caaa835a609cc598f8480b0741eb1e115f80c54f077c2876df3970b9378144`。冻结总证明 `9157b518ed35bd13caf693b0457d8157113c55c1e266b68eb8240148618c76ff`，3,503 当前路径；检查器 exit 0，共享 GPU OS 锁实际未持有。

本轮 S0 新模型/框架/GPU/编码/数据构建/下载/安装均 0，未运行生产测试。E1 的实际新身份/intake、完整候选/CPU 证据、R1、最终 CI/main 均待完成。后续真实参数、容量、零 LoRA/冻结底座与 adapter 重载须另有运行证据；不存在正式模型训练、评测或服务验收。
