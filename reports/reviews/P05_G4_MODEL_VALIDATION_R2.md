# P05 G4｜批次模型文件验证复用 R1 审核 r2

2026-10-26，独立技术审核者 R1 AI。结论：**PASS，新增阻断项 0。** 本轮支持接纳批次文件验证复用的 CPU 实现，并由 S1 冻结一次独立运行时诊断。实际 CUDA 加速及诊断轨迹尚未运行；原 80 条、0 成功/0 偏好结论保持。

受检原提交 `db5cbacf25499f5d1fa5ae66853eb5f3d66ef35f`，S1 集成提交 `500d9dce4b66762efb72e3ed93a07ac3baa9454b`，实现授权 `3890349baeb7f262230873bd0f52b4d05deeca4e`。范围依据[任务](../../coordination/tasks/P05_G4_MODEL_VALIDATION_CPU_R2.md)，实现说明见 [T1 报告](../P05_G4_MODEL_VALIDATION_R2.md)。R1 从集成提交独立审阅四份生产文件差异；8 个候选文件与原提交、集成树和 T1 索引逐字节一致。

## 已验证的边界

- 每次生产 `execute` 在启动候选前调用一次完整 `validate_model_files`，将所得 `ModelFiles` 通过 backend 传给 owned child。公开请求没有外部验证缓存字段；没有持久缓存读取或文件变化后静默重验的路径。父进程不导入 Torch。
- child 的 `load_model` 在加载前、LoRA 附加及设备搬运完成后各调用一次 `recheck_model_files`。固定配置、model/revision/root、声明文件集合、字节数及哈希身份均受约束；目录与文件 stat 包含 device/inode/size/mtime_ns/ctime_ns，逐级打开保持 `O_NOFOLLOW`。T1 的真实小文件反例覆盖同大小改写并恢复 mtime、inode 替换、文件/父目录 symlink、额外文件和错误绑定；加载期间变化由明确标记的 MOCK_ONLY 加载边界检查覆盖。
- 原 lease、checkpoint 字节验证、adapter 实参 hash、BF16 底座/FP32 adapter、完整输入、seed/decode 和 30 秒轨迹 deadline 保持。SFT/DPO 原调用未传入复用对象，仍走完整验证。既有接口证据适用，未重复运行训练或整套矩阵。
- `execute` 的段计时起点在预检之前；预检单列于 `model_file_preflight_seconds`，并计入 segment 和外层分配成本。动态耗时和 stat 不进入 batch hash；固定策略 `batch_full_hash_child_stat.v1` 进入执行身份。恢复仍只启动未 started 的 ID，原 started/terminal 字节继承逻辑未改。child 冷加载明确标记为排除批次完整预检，不能直接与 r1 冷加载相减宣称收益。

## 独立检查与复用证据

R1 核对 T1 索引的 13 份证据、7 份最终命令回执及其中的实际源码哈希。以下 47 项是复用的已执行检查，不记作 R1 新跑；修订前 11 项缺少复用接口的失败及其记录保留。

| 证据 | 结果 |
|---|---|
| T1 `tests-loader-after.json` | 14 passed，exit 0；文件身份、加载前后检查和默认完整验证 |
| T1 `tests-batch-after.json` | 16 passed，exit 0；每次 execute 预检、段预算、恢复身份与进程回收 |
| T1 `tests-interfaces.json` | 17 passed，exit 0；固定 metadata、输入、decode、adapter 与 deadline |
| R1 `intake.json` | exit 0；候选/回执绑定、未变函数及诊断原始输入回读 |
| R1 `cpu-probe.json` | 1 项独立 CPU 进程检查通过，exit 0 |

独立检查使用现有原创小文件，仅替换固定 metadata 的 fixture 入口。父进程真实哈希全部 4 个文件后，将完整对象交给实际 `OwnedProcess` spawn child；未变文件前检查通过，child 模型文件哈希次数为 0。在前后检查之间原位改写再恢复权重字节，并恢复原 mtime，最终字节、inode、大小和 mtime 均相同，ctime 已变，后检查及父进程对旧对象的复查均报 `file_changed`。另一次显式完整验证重新哈希 4 个文件后才接受恢复后的字节。child exit 0、已回收；父子进程均未导入模型框架。

实际新命令如下，绝对参数、环境和 stdout/stderr 保存在对应私有回执。`PYTHON` 为已授权的既有 CPU 解释器，`R1_PRIVATE` 为交付中的审核证据目录；环境未修改。

```sh
"$PYTHON" -B "$R1_PRIVATE/run_check.py" intake "$PYTHON" -B "$R1_PRIVATE/intake.py"
"$PYTHON" -B "$R1_PRIVATE/run_check.py" cpu-probe "$PYTHON" -B "$R1_PRIVATE/cpu_probe.py"
```

## 单条诊断脚本只读审核

受检 `runtime-diagnostic.py` SHA256 为 `c951acfe94069f0ffd40f4cb405d2b04bf31dd1ecd4588030b33f76412f5cc40`，只读审核 PASS，未导入或执行。脚本显式完整预检一次，再将本次对象传给原 CUDA backend；只调用一次原 LocalHarness。选取 **ordinal 8，即第 9 条，seed 50**，segment 上限 90 秒，轨迹仍由原 harness 限制为 30 秒；`max_trajectories=9` 用于原清单索引，实际诊断次数固定为 1。结果采用独立诊断身份、`formal_training_eligible=false`，新输出目录要求不存在，原失败不被替换。

R1 回读了 [Q1 审核](P05_G4_PREFERENCE_Q1_R1.md)绑定的原 run、batch、80 条候选文件及 tasks，核对 ordinal、seed、首输入和 terminal hash 一致。原样本确有 3 次输入、2 个完整返回动作，第三次请求后超时。原 terminal 行 SHA256 为 `6738ac922ab2ab0c0a51bc8261afc40145cf854fd434ec727d41125df44716d0`。诊断可检验第三次请求是否完成及是否返回合法 final，不能预先推断语义成功。

外层 `supervise` 使用既有 owned-run/source 校验、独立进程组、段/分配剩余时间上限及超时回收。S1 实际启动前仍须冻结 CI 已通过的 main、run/control/authorization 的一致身份、脚本/config hash 与分配预算；本次静态审核不构成 GPU 已运行或最终配置已冻结的证明。

私有证据索引 `.toolalign-local/review-p05-g4-model-validation-r2/evidence-index.json` SHA256：`b3909f3bbb17fc4e2ee2e115dc3f3bce52bdc50eae46e2e8903de7d72877451f`。公开交付仅本报告及[交接](../../coordination/handoffs/P05-g4-model-validation-review-r2.md)；生产源码、共享状态、旧审核和 S1 脚本均未修改。正式 DPO 继续未放行。
