# P04-SFT-NATIVE-TOY-R1｜原生数值与资源终态独立审查

状态：IN_PROGRESS。S0 于 2026-09-06 19:36:51 UTC 按完整授权 `482f8991c97c33678583aa6c853a75c41fda0f0f` 实际原生派发，并核验 R1 新轮 ACTIVE/inProgress；19:47 UTC 完成实际新分支、408 候选、13 授权副本与旧制品的 intake 核验。独立结论待交付。本文件给出新的独立审查范围，不改变 T1 原运行额度或正式训练门槛。

| 字段 | 本轮值 |
|---|---|
| owner | R1，复用已结束上一轮的独立 Codex 任务与隔离 worktree |
| 精确候选 / code_base | `f7326d1823c4cf132ae44525f4755c96c88ec159` |
| tree / parent | `247eba004d714def81f0bef65375ddbf0fee95cf` / `c06782a61857259097932078c661189b4fda781d` |
| 实现基线 / T1 原授权 | `50867c0be43d110df6c3620c94022fcfdaf779b5` / `de86568d73ee77bbf92b6f749a39a9ab38955836` |
| authorization_commit | `482f8991c97c33678583aa6c853a75c41fda0f0f`，切换前读取并私有保存 |
| 新 branch | `review/p04-sft-native-toy-r1`，从精确候选新建；保留原 CPU review 800480b 及其他旧 refs |
| 模型 / 推理 | `gpt-6-astra` / `max`，不创建其他任务或 sub-agent |
| 协作 / 契约 | plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0021 |
| 交接 | `coordination/handoffs/P04-sft-native-toy-review-r1.md` |

先读授权提交的 AGENTS、PROTOCOL、PROJECT_STATUS、本文件、[T1 原任务](P04_SFT_NATIVE_TOY.md)、[固定 S0 配置](P04_SFT_NATIVE_TOY_CONFIG.v1.json)、ADR-0021、docs03/16、[S0 完整交接证据](../../reports/S0_P04_SFT_NATIVE_TOY_HANDOFF.md)及[源码中间证据](../../reports/S0_P04_SFT_NATIVE_TOY_INTERMEDIATE.md)。随后读取精确候选的 9 条改动、T1 handoff/REPORT/VALIDATION 和私有原件。S0 的对照值与 worker 自测是审查输入，不代替 R1 的独立判断。

## 所有权与保全

只新增 `reports/review/P04-sft-native-toy-r1/` 中的审查、去敏索引与必要原创小探针，以及本轮交接单。被审 408 文件全部只读；不能改候选实现、配置、原测试、锁/CI、公共协调或其他 worktree，也不能修复后给原候选签通过。独立发现问题先给最小可复现实证，继续冻结本候选整包结论，修订另由 S0 派发。

切换前核验原 CPU review `800480b0b1e14c21937f1b5073daf543a2ba31fc`、旧分支和原私有文件，保存本轮保全清单。保留所有旧 FAIL、review 原 SHA，以及仅在本机保留的原 f708；不得令 f708 成为公开祖先。禁止 reset/rebase/force-push、覆盖旧运行目录、合入较新 main、改变 S0 goal 或向 S0 回报时更改模型设置。新私有总量最多 2 GiB；写入均在 R1 本轮新目录，现有目录拒绝覆盖。

T1 delivery SHA-256 为 `e3145eafd84eef3a8f316f8fb8a4f4a124b4a6662ca12796987fc0365bc9203b`，FINAL_FILES 为 `5a266eac20dd5e44db90b23711ca580b624d7cf071462c6da0e6fac6056eb1e0`。S0 精确交接证明为 `b3b3e5b54abcc451f76e8731d72e00b516373b2f3f297abcacfabc0a48082f26`；本机路径由原生消息提供。不可执行会写回 T1/S0 原目录的辅助脚本。

## 必须独立核验

1. 全部 9 条授权改动与 399 份不变基线、精确配置 `fb06634d00b0565a60dc22ea829ac509732b3b6429b9bbbc2ff6207c974850cb`、原 cases `df4b87001074e9fab6c3a330cf516dca17cfab1bb7505d97025ceeb31d3b5b47`。原生成器/CPU 配置/默认 CPU 入口保持；新增 native 消费源码纳入其真实身份。`training_authorized=false`、固定原创输入、FORMAL/跨 profile 拒绝不能被新入口绕过。
2. 直接核对全部原 13 rank 的数组、初始 64 参数、shift/EOS/右 padding 与分母。rank 1 和 13 原数值相同，不能去重或换例；从原定义独立推导监督位置及 CE/完整梯度，而非仅复用 T1 已算出的参考。核对逐例 MLX/Torch、去 padding 和忽略 logits 改动，以及 default_loss 多监督一个 padding 的真实负例，float32 atol 固定 2e-6。
3. 审查原生 train/evaluate/TrainingArgs/loss/iterate_batches 和 compile 保持。8+5 必须真实做两次 SGD 更新、分别除 8 和 5、原 13 rank 各一次、同一 model/optimizer/RNG 不重置；checkpoint 参数逐内容与独立更新参考比较。核对原单段 accumulation=8 的真实一次更新/丢 5 尾微步，不以 EXPECTED_NEGATIVE 进程 exit 0 宣称训练正确。
4. 审查每个实际 checkpoint 后完整 native evaluate、44 token 的加权分母、选择/validation/参数/文件/step/microsteps 身份绑定、尾部更新后的新 score、实际保存重载与错误 checkpoint 拒绝。两个 score 的确定性选择、CPU/GPU 不混选、FORMAL/未知 scope/profile/无效数值/身份/分母拒绝需有独立边界检查。toy 验证重用训练样例仅证明状态记账，不能报告泛化或模型质量。
5. 当前真实 PID/启动时间/物理 lock 文件 fd/owner 与仓库一致，框架导入前持有共享 OS 租约；GPU default/stream 和 Torch CPU/2+2 线程真实。原 P01 wired-limit 上下文仅抑制 OS setter、保留事件并恢复原 API；不修改该模块或 vendor，不伪造 metadata/数值、不关闭 compile。审查 wall/RSS/MLX peak/启动次数和异常退出的实际控制路径。
6. 独立复核原磁盘超限后丢 supervision 的反例及 fae3d60 修复，使用少量真实自有 CPU 子进程测试 monitor/最终诊断失败时 cleanup、终态和失败模式重登记。可以使用小文件和缩小的测试阈值或明确标记的故障注入，不真实写满 2 GiB，不让测试改生产限额或共用 T1 ledger。S0 已有原 CPU 复现和两项修复回归，R1 仍独立判断覆盖；区分诊断无法取得和成功取得的数值。
7. 原始源码运行 epoch 为 534445b，修复后生产为 fae3d60，安装 probe 为 c06782a，最终 f7326d1 仅加文档。核对 31 原命令、27 测量子集、7 源码快照/409 blob、提交前 guard 的原 hash 及明确重构记录。所有原失败、两次 semaphore shutdown warning、误分类诊断和中间归档保留；只读检查确切历史 semaphore 不等于全局泄漏审计。
8. 独立运行适用完整 CPU 组及新审查探针。T1 基线为 931+60+2+13+44=1050 passed、2 HF-only skips，新 36 已含其中，110 subtests 另记；不修改收集或旧断言、不把重复运行加到独立计数。使用现有默认/纯 tokenizer 环境、新系统临时 basetemp（不可置于被扫描的私有祖先）；真实 tokenizer 测试使用已有固定 source 路径。Ruff、4 契约冻结、公开扫描和 diff 检查完成，保留全部 argv/环境/UTC/exit/日志/skip 原因。
9. 核对实际 sdist 122 成员、默认/显式 sdist 重建 wheel 各 63 成员、58 包载荷与 Git、metadata、entry points、license、完整 RECORD 及默认 wheel 来源。离线 `--no-deps` 安装到 R1 新 target，非源码 cwd 验证默认 prepare/帮助/拒绝和新 native 的纯导入/guard；实际来源来自新 target、无可选框架导入/源码回退。原 CPU prepare 的历史消费 hash 不改写。可直接使用已完整绑定的实际 wheel；额外新构建仅在独立证据需要时进行，不机械重建未变字节。

## 本轮 R1 的独立框架许可

本条是新授权，独立于已结束 T1 的五次额度。R1 本轮 **最多 2 次 framework 子进程启动，失败计入**；至少一次应为实际新安装 target 的固定原 13 例 segmented 验证。第二次仅用于首次探针真实失败后的限域修订，或 R1 明确说明还需直接观测的原单段尾批反例；不无差异重复已成功路径，耗尽后保留结果并交 S0，不自行增额。每次启动前保存模式/准确代码及输入/资源额度，单独新目录与 R1 私有 ledger；不得写 T1 ledger、运行目录或继续 T1 剩余额度。

每次严格限原 13 例、8×8/64 个 float32 参数、16 token 桶、词表 8、seed 42、SGD0.07；每 backend 最多 2 更新、wall≤300 秒、RSS≤4 GiB、实际 MLX peak≤1 GiB、Torch intra/inter-op 各≤2。只读复用现有已锁 replay 环境，版本与 trainer/datasets 原 hash 均核对；不新建环境/下载依赖。取得同一物理 `gpu0` OS 租约后才导入任何框架、设置 GPU default/stream，随后建数组；租约持有至真实进程退出，异常/超限只终止、wait/reap 本轮自有进程，保留 PID 不存在与锁释放。

独立审查包装器可以调用安装版已冻结的 `_numerics`、有限适配与真实上游公开接口，但不能复制上游训练循环、替换数值或伪造计数。R1 的实际租约 owner 应如实使用 worker_alias=R1；native 校验所需 task_id 保持 `P04-SFT-NATIVE-TOY`，另在 R1 原始记录绑定本审查任务及授权。原 T1 CLI 的固定 worker label 不应被冒充为 R1 的真实身份；包装器只解决独立进程/记录/租约边界，候选所有源码保持只读。默认入口/监督器本身另外经 CPU 与原 T1 实际安装运行证据审查。新运行必须保存完整真实数值、checkpoint、score、raw stdout/stderr 和所有实际模块 origins。

除这些固定原创数值外，无预训练权重、真实 P02 优化、新实际 10+3 例或 8,228 行编码、选择重新物化、baseline/容量/SFT/DPO、BFCL、网络 tracker、服务、费用或模型/数据上传许可。原 100/13 人工表只允许 kris 填写，实际页面导航拒绝保持，不换浏览器/localhost/代理绕过；人工、G-DATA 与正式 P04 均不由 R1 代签。

## 结论与交接

给出精确候选的 PASS/FAIL/BLOCKED 与 P0/P1/P2，分别说明默认 CPU 行为、新原生 toy 数值/状态绑定和资源终态。原 CPU 上游 KeyError 仍是有效历史负结果，不要求本候选修复 CPU trainer 支持；正式模型能力不在此次结论内。非阻断建议不升级成无限平台工程。

最终只提交本轮审查目录和交接单，审查提交直接以精确 f7326d1 为 parent，不合入其他分支。保留新原命令/数据/源码/归档/来源/资源证据与原制品；普通推送新 review 分支，向 S0 提供完整 candidate/review/parents/tree、结论和私有封存 hash 后结束。独立 PASS 仍不自动关闭最终 CI/main 或完整 P00–P09 目标。
