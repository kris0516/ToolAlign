# P04-SFT-NATIVE-TOY 原生接口数值交付

状态：`SELF_TEST_PASS_PENDING_INDEPENDENT_REVIEW`。本轮原创 toy 的源码与安装版分段运行均通过；上游单段运行真实复现尾部 5 微步没有更新。完整 P04、正式训练、真实模型评测与人工门槛仍未完成。独立 R1 与 S0 最终验收待进行。

T1；`gpt-6-astra / max`；分支 `work/p04-sft-native-toy`。code base 为 `50867c0be43d110df6c3620c94022fcfdaf779b5`，授权为 `de86568d73ee77bbf92b6f749a39a9ab38955836`。规划/契约版本保持 `plan-v0.1`、`coordination.v1`、`toolalign.contracts.v1`，本轮范围来自 ADR-0021。机器为已授权 Apple Silicon 本机；记录的运行时间使用 UTC。

配置 [sft-native-toy.v1.json](../../configs/sft-native-toy.v1.json) 与 S0 原件逐字节相同，SHA-256 为 `fb06634d00b0565a60dc22ea829ac509732b3b6429b9bbbc2ff6207c974850cb`。固定输入文件 SHA-256 为 `df4b87001074e9fab6c3a330cf516dca17cfab1bb7505d97025ceeb31d3b5b47`，原生成代码 SHA-256 为 `3872ed4187b0754b9baa32525a6aa3b157e33c0d7ceb7b9d1336f34df4536ed0`。13 个固定样例 ID 对应 12 种不同数值载荷：rank 1 与 rank 13 相同，原顺序、重复项及全部原数组均保留。

输入为词表 8、8×8 的 64 个 float32 参数、padding 桶 16、EOS 7、pad 0。验证重用这 13 个 ID，仅检查参数与状态记账；每次完整验证分母为 44 个监督 token。没有新的真实 P02 10+3 例编码、8,228 行重新编码或选择物化。

实现新增显式 native 入口，先核对固定配置、输入、真实当前 PID 的共享租约及物理仓库，再导入框架。MLX 设置 GPU default 并在 GPU stream 中执行；Torch 为 CPU、intra/inter-op 各 2 线程。默认 CPU 入口与其 CPU 设备限制保留。共用内部适配器通过原生 `TrainingArgs`、`train`、`evaluate`、`loss`、有限 `iterate_batches` 注入点执行，上游 compile 保持原对象。

依赖从原 replay 环境只读核对：MLX 0.32.2、MLX-LM 0.31.3、Torch 2.14.0、NumPy 2.5.2、psutil 7.2.2。trainer/datasets 源码 hash 分别为 `ee33ebdbd20a184108541cb490d08085485e71a82ffd6d68d7d216029ecd28fe`、`fa112840e6ea98a4ff18428792fe2ab023999c2da51ea64b3ebdf8657a152f17`。

| 实际运行 | 结果 | MLX 更新 | 已处理微步 | wall 秒 | 采样峰值 RSS 字节 | MLX peak 字节 |
|---|---|---:|---:|---:|---:|---:|
| 源码 segmented | PASS | 2 | 13，8+5 | 5.215604 | 399605760 | 5864 |
| 源码 unsegmented | EXPECTED_NEGATIVE | 1 | 13，尾部 5 未更新 | 2.962632 | 387514368 | 5864 |
| 安装版 segmented | PASS | 2 | 13，8+5 | 3.407459 | 402309120 | 5864 |

总计 3/5 次真实 framework 子进程启动，framework 子进程失败 0 次，未使用两次修正余量。负例进程退出 0 表示成功捕获不完整更新。三个主子进程均真实 wait/reap、原 PID 不存在、实际租约释放；租约在每个进程退出前保持。以上时长包括该小进程的工作，不用于外推模型吞吐。DLPack `(8, 0)` 仅记为硬件互操作标签；执行证据为实际 GPU default/stream 和 Torch CPU。

13 例逐例保存原 token/attention/loss mask、CE、有效分母、MLX 与 Torch 的完整 64 元素梯度、去 padding 梯度，以及修改忽略位置前后的 logits。独立 Torch 参考从原边界计算监督位置。最大绝对误差如下，固定容差为 `2e-6`：

| 检查 | 最大绝对误差 |
|---|---:|
| 逐例 MLX CE / Torch CE | 2.384185791015625e-7 |
| 逐例完整梯度 | 4.470348358154297e-8 |
| 右 padding 的 CE / 梯度不变 | 0 / 0 |
| 改变忽略位置 logits 后的 CE | 0 |
| 第一次实际 checkpoint / Torch 参数 | 1.862645149230957e-9 |
| 第二次实际 checkpoint / Torch 参数 | 1.862645149230957e-9 |
| 第一次 token-weighted validation / Torch | 2.0590695459787867e-7 |
| 第二次 token-weighted validation / Torch | 9.211626927907446e-8 |

SGD 为 lr 0.07、无 momentum/weight decay、seed 42。8+5 两段保留同一 model/optimizer/RNG 对象，实际分别除以 8 和 5。两份 Torch 更新参数与梯度在调用 MLX 训练前已保存；每个实际 checkpoint 的原始 safetensors、重载参数及比较数组均保留。逐 checkpoint 的原始字节又经 stdlib 解析，与实际数组及参数内容 hash 复核。

两个实际 score 的验证 CE 为 `2.066978758031672`、`2.0616965131326155`；最小有限 CE 规则选择 step 2。其参数内容 hash 为 `0c4907f87df8c5d58efd31e3ba40a14fa6a5a28d3342c4394905ae6ad091a2dd`，checkpoint 文件 hash 为 `17906c78b9689f4e75768eb2bbe23ce5853db2a66833e295b10b2fa9436eb132`。源码与安装版的两份 score 记录完全一致。尾更新后保存重载再次评估相同；把第一次 checkpoint 绑定第二次参数实际触发 `checkpoint_parameter_content_mismatch`。

上游单段 accumulation=8 的实际最终参数等于第一更新状态，与完整两次更新参考相差 `0.013687163591384888`。上游 `default_loss` 的原反例也实际保留：把一个 padding 位置计入监督，分母 3，正确分母 2。两者均为真实负例。

原 `preserve_wired_limit` 模块未修改；每次抑制的 OS setter 请求及原 API 对象恢复均有记录。源码与安装版 segmented 的 stderr 各有一条 `resource_tracker` 单个 semaphore 的关闭清理 warning。原日志完整保存；只对日志中的两个确切名称执行 `sem_open(flags=0)`，修正后的 Darwin `SEM_FAILED` 只读探针均得到 `ENOENT`，无创建或 unlink。这只说明这两个历史名称在检查时不存在，未进行全局泄漏审计。首版只读诊断对 sentinel 的误分类及随后 SDK 包装头检查失败亦保留，没有据此重跑数值。

源码数值的真实 epoch 为 `534445bb8eecd600b65e90e541cd30601b4fd07c`。S0 随后发现磁盘超限后的最终统计再次抛错，会阻止写入 supervision；修复提交为 `fae3d608b6edc3f5dc941dfb3395757ee3db2ef3`。最终探测逐项捕获错误，保留失败终态；child 诊断写入异常仍确保 OS exit。两个新增 CPU 场景用真实自有小进程写 5000 字节、越过缩小的 4 KiB 测试阈值，验证 terminate/wait、PID 消失、临时仓库租约释放、重复磁盘/锁诊断失败留证与失败 mode 可重新登记。生产 2 GiB 上限保持。

已通过的源码数值没有重跑或改写 epoch。跨修复提交的数值函数 AST、MLX 适配器和 validation 文件保持一致；最终安装版实测新的监督器。安装 probe 修订后的命令 epoch 为 `c06782a61857259097932078c661189b4fda781d`，生产字节与 `fae3d60` 相同。最终 `native_toy.py` SHA-256 为 `f4ce51fecad6bc914f806a9cd53c631166651212503ae5e376a32eb01a0aaedd`。

| 最终 CPU 组 | 结果 |
|---|---:|
| 当前组合，含新增 native 守卫 | 931 passed / 2 HF-only skipped |
| 原格式独立组 | 60 passed |
| 截止时间独立组 | 2 passed |
| 训练绑定独立组 | 13 passed；110 subtests 另记 |
| 原 SFT 独立组 | 44 passed |
| 不重复计数合计 | 1050 passed / 2 skipped = 原 1014 + 新 36 |

原测试收集与断言保持。新测试涵盖配置/输入字节篡改、当前真实租约、错误物理仓库与描述符、空分母、样本/序列/词表/参数边界、输出复用、scope/profile、跨 CPU/GPU 选择、启动限额及真实收尾失败。Ruff、4 份契约冻结与公开扫描通过。重复 guard 运行、安装检查与数值复现不增加独立 pytest 计数。

实际从最终生产字节构建 sdist、默认 wheel 和显式 sdist 重建 wheel；归档逐成员对 Git、metadata、entry points、license、完整 RECORD 验证。新 target 离线 `--no-deps` 安装，非源码 cwd 的 15 条 CPU 安装命令通过，9 个 SFT 模块的真实 origins 已核对，无可选数值框架导入；新 native 及两个修改模块在 GPU 安装版运行中也全部来自 wheel。默认 CPU prepare 使用新消费 hash `4df0d2da491de0dd0abf4fdf7cc64ce733f475fce38617d07f4e7d3c72baf491`，原 `52cd77a0…` epoch 未改写。

| 归档 | 成员数 | SHA-256 |
|---|---:|---|
| sdist | 122 | `b8c29ecad579ec43a06b31b9d6106d669dc74c0c50c13d785c861cff46062a17` |
| 默认 wheel | 63 | `0373c1adb1ae784391e82b06f6c93ab1519f593e68fec4c14c629829f83b5d3b` |
| 显式 sdist 重建 wheel | 63 | `0373c1adb1ae784391e82b06f6c93ab1519f593e68fec4c14c629829f83b5d3b` |

默认 wheel 由该次实际 sdist 构建。普通源码直接构建 wheel 为 `NOT_RUN`。没有新环境、依赖下载、预训练权重加载、真实 P02 优化、模型/数据上传、服务或费用。

如实保留的其他历史失败：首次父进程因本轮 CPU 测试构造的符号链接被磁盘统计拒绝，尚无 framework launch；首轮完整 CPU 装配因 basetemp 含私有目录名称、缺少 tokenizer 路径，实际为 881 passed / 2 failed / 48 skipped；首轮安装来源 probe 未导入默认 `__main__`，9 模块计数断言失败。后两项分别纠正运行环境和报告脚本，在独立新输出中重新验证。原日志与中间归档均保留。

[机器可读统计索引](P04_SFT_NATIVE_TOY_VALIDATION.json) 绑定封存时 27 份原命令回执，含真实 argv/cwd/环境/UTC/退出码、完整日志 hash 与各自真实源码 epoch。私有来源快照共 7 组、409 个去重源码 blob；三次提交前 guard 原执行 HEAD 保留，匹配后续提交或原已记录内容 hash 的快照，没有伪造重跑。完整数值数组、路径、任务映射与日志仅存私有交接位置。

原 P01/P04 两个 refs 与 1559 份旧私有制品全部 hash 不变；base 的另外 399 份文件保持。原 R1 CPU review `800480b0b1e14c21937f1b5073daf543a2ba31fc`、两次 CPU 失败及其限制保留。测量封存时新私有文件共计 31013875 字节，后续最终封存另记录实际总量。原始测量清单 SHA-256 为 `b0f641aeaa9fa6c6c394d588ab6457259f0cf878da00377181a3ef785e0907c4`。

复核入口为固定配置的 `toolalign.training.sft.native_toy` 显式 CLI、[安装验证脚本](P04_SFT_NATIVE_TOY_PACKAGE.py) 和 [CPU 守卫测试](../../tests/training/sft/test_native_toy.py)。原完整命令及新输出位置在私有回执中；成功 mode 会拒绝重复。本轮结束后未用额度不转授，R1/S0 新 framework replay 需要其后续独立明确范围。
