# P05 G4｜批次模型文件验证复用 r2

2026-10-26，T1。按授权提交 `3890349baeb7f262230873bd0f52b4d05deeca4e` 的[任务](../coordination/tasks/P05_G4_MODEL_VALIDATION_CPU_R2.md)完成 CPU 修订。生产 `execute` 每次完整验证固定模型文件一次；随后各独立模型 child 在加载前后检查固定身份和文件 stat，复用本次内存中的验证结果。47 项受影响 CPU 检查通过，R1 独立验收待运行。

修订依据是[原始生成与诊断报告](S1_P05_G4_GENERATION_R1.md)：80 条正式候选冷加载中位数 19.083 秒；另一次 cProfile 诊断中 `validate_model_files` 累计 12.230 秒，SHA-256 update 自身 11.015 秒。T1 回读了原诊断 run、脚本、候选文件的 SHA256，并核对候选内的完整 phase profile 与 S1 intake 相等。插桩冷加载 21.807 秒含 profiler 开销，不能与 19.083 秒直接相减作为优化收益。

## 实现与身份边界

`cuda_generate.runner.execute` 在任何模型 child 启动前调用原 `validate_model_files`，完整读取固定文件并验证哈希、配置和 safetensors header。`ModelFiles` 现在保存验证时的目录 stat；已有 `FileIdentity` 继续保存各文件的 device、inode、size、mtime_ns、ctime_ns。

`recheck_model_files` 接受当前父进程完整验证所得、传给 owned child 的内存对象。它核对模型路径、model/revision、固定 metadata、文件名集合及各文件的已验证字节数/哈希，并复用原有逐级 `O_NOFOLLOW` 打开和 stat 检查。目录 stat 同时约束批次期间的文件集合。内容改写后恢复 mtime、文件替换、symlink、目录变化或错误绑定均明确拒绝；不会重新哈希后静默接受新文件。没有从 run/config/磁盘读入缓存 metadata 的入口、跨运行缓存或常驻模型服务。

`cuda_sft.engine.load_model(..., verified_files=None)` 保留原默认完整验证路径，SFT/DPO 调用点未改。生成显式传入已验证对象时，先检查，再执行原模型加载、LoRA 附加和 CUDA 搬运，最后再次检查文件。原 checkpoint 验证、adapter 恢复和实际参数 hash、BF16 底座/FP32 adapter、lease、父子进程边界与框架导入顺序保持。

完整 ModelInput、模板、seed、decode 和每轨迹 3 次决策/2 轮工具/256 新 token/30 秒 deadline 均保持。父进程预检只读文件和 JSON，不导入 Torch 或加载模型。

## 计时与恢复

| 字段 | r2 含义 |
|---|---|
| `summary.model_file_preflight_seconds` | 当前这次 `execute` 的完整模型文件预检耗时；不累计继承段的预检 |
| `summary.segment_wall_seconds` | 从 `execute` 进入时计时，包含源/环境检查、完整预检和后续批次执行；预检耗尽预算时不启动候选 |
| `identity.model_file_validation` | 固定值 `batch_full_hash_child_stat.v1`，进入 batch identity；绑定新的执行方式 |
| `backend_metrics.cold_load_scope` | 生产复用路径为 `tokenizer_through_cuda_ready_excludes_batch_file_preflight` |
| `summary.cold_load_scopes` | 已记录 child 冷加载的范围标签 |

child 的 30 秒仍由原 LocalHarness 计时，涵盖首次 tokenizer/输入编码、框架导入、checkpoint、模型加载及文件前后检查、adapter 恢复和推理。批次完整文件预检计入 segment，外层 Colab 分配时间继续覆盖全部预检成本。r2 的 child 冷加载数值因此与 r1 不同口径，比较必须同时报告批次预检和 segment 成本。

预检耗时和文件 stat 不进入 resume batch hash。每次新 `execute`、重启或新实例均重新完整验证；已有终态和 started 记录的恢复规则未改，只继续未启动 ID。r2 的固定执行方式和源码身份与 r1 区分，不迁移、覆盖或重跑原 80 条终态。单独构造 backend 而不提供验证结果时仍完整验证，并标记 `child_full_hash.v1`。

## CPU 证据

使用已有专用 CPU 环境，Python 3.12.14、Torch 2.8.0、Transformers 4.57.6、PEFT 0.18.1；未安装依赖。私有证据位于 `.toolalign-local/p05-g4-model-validation-r2/`，实际绝对命令、退出码、stdout/stderr 和源码文件哈希保存在对应 JSON 回执。

| 回执 | 实际结果与范围 |
|---|---|
| `tests-before.json` | 修订前 11 项失败，原因均为尚无复用接口；原记录保留 |
| `tests-files-after.json` | 首批 11 项文件检查通过；为下一行的子集，不重复计数 |
| `tests-loader-after.json` | 14 passed，exit 0：首次真实文件哈希、未变复用不再读取权重、同大小改写并恢复 mtime、inode 替换、文件/父目录 symlink、额外权重、错误绑定、加载过程中变化及默认完整验证路径 |
| `tests-batch-after.json` | 16 passed，exit 0：每次 execute 一次预检及内存传递、成本进入段预算、动态计时不改变恢复身份，以及原 started/terminal、故障队列、预算、恢复与 child 回收检查 |
| `tests-interfaces.json` | 17 passed，exit 0：固定公开 metadata、原 loader 接口、完整输入/overflow、deadline 回收、decode 参数和 adapter 实参校验 |
| `ruff.json` | 变更 Python 文件检查通过，exit 0 |

文件测试使用原创小文件，仅替换固定 metadata 的测试入口，真实执行文件读取、哈希与 stat 检查；模型加载边界测试以少量 CPU 张量和明确标记的 MOCK_ONLY 加载/设备搬运替代真实模型。批次测试使用原 scripted CPU harness；生产调度测试不启动模型 child。以上共 47 项不同的通过检查，不构成真实 CUDA 性能结果。

真实 L4 优化后冷加载、完整轨迹与模型效果仍 NOT_RUN。原 80 条的 0 成功/0 偏好结论不变；本次文件验证修订不声称解决动作类型、终止监督或 DPO 质量。后续由 R1 独立验收，再由 S1 冻结另一次小型 GPU 诊断。
