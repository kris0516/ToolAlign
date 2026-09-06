# P04-SFT-CPU-R1｜CPU 准备与已知上游限制独立审查

状态：IN_PROGRESS；S0 于 2026-09-06 16:05 UTC 核验原轮 completed/idle 和干净 40252f8 后，按完整 d65592e 原生派发，新轮 ACTIVE 已确认；R1 已于 16:16 UTC 切至精确候选的新分支，S0 于 16:22 UTC 核验 384 候选/13 授权副本与旧 1562 封存文件，intake 通过，正式结论待交付。T1 最终候选已交付、普通推送并核验原生 completed/idle；S0 已核对 2083 个文件路径及原始命令/归档/安装。被审交付明确为 CPU_PARTIAL_UPSTREAM_BLOCKED，不是完整 trainer 或正式 P04。

| 字段 | 本轮值 |
|---|---|
| owner | R1，既有独立 Codex 任务与隔离 worktree |
| 精确候选 / code_base | `33d6248e2c518ea777618224382bd30a3cc3433d` |
| tree / parent | `1d2d5474ef87034e0184f8ebfa359345182e3356` / `0c7c2671a64d49fe48c722375481b4cf7a5c82c8` |
| 实现基线 / T1 原授权 | `42eaa50a9519efe96d60b49f07cfbd106b36778c` / `e42536dd7c77d90ed33ab5354f288ab0f1c3d6c6` |
| authorization_commit | `d65592e5529f573f061355775fec071737233d12`，原生分发的完整协调 SHA，切换前读取并私有保存；后续状态补记不改被审范围 |
| 新 branch | `review/p04-sft-cpu-r1`，从精确候选新建，保留旧 `review/p02-training-binding-r1` / `40252f8` 及全部旧 refs |
| 模型 / 推理 | `gpt-6-astra` / `max`；不创建新任务或 sub-agent |
| 协作 / 契约 | coordination.v1 / toolalign.contracts.v1 / plan-v0.1 / ADR-0017 至 0020 |
| 交接 | `coordination/handoffs/P04-sft-cpu-review-r1.md` |

先读本授权的 AGENTS、PROTOCOL、PROJECT_STATUS、本文件、[T1 原任务](P04_SFT_CPU_PREPARATION.md)、[S0 原配置](P04_SFT_CPU_CONFIG.v1.json)、ADR-0020、docs03/16、[S0 中间证据](../../reports/S0_P04_SFT_CPU_INTERMEDIATE.md)和[完整交接核验](../../reports/S0_P04_SFT_CPU_HANDOFF.md)。随后读精确候选的全部 20 个新增文件、T1 handoff、REPORT、UPSTREAM_LIMIT、VALIDATION 索引与原始私有回执。旧聊天与 worker 自测不能代替独立判断。

## 所有权与保全

只新增 `reports/review/P04-sft-cpu-r1/` 的审查、去敏索引和必要原创小探针，以及本轮交接单。被审 384 文件全部只读，包括配置、8 个新生产模块、原测试和报告；不能修实现后给原候选签通过。只写 R1 本轮新的私有目录，现存即拒绝覆盖，新增私有总量不超过 2GiB。

切换前保存原 `40252f8517f3c7ac8ddc0340847946ac902200e1`、旧分支/refs、上轮审查与原私有制品清单。保留所有旧 FAIL、原未去敏 f708 本地提交且不使其成为公开祖先。不得 reset/rebase/force-push、合入后来 main、改变依赖/锁/CI/契约/公共协调、其他 worktree 或 T1/D1 旧私有证据。不创建或更新 S0 的长期 goal。

T1 最终 completion SHA 为 `7cc60a30519b6f6011b33616b40a8b24a3712d813e48051ec6b04d33c823e151`，机器索引为 `ba93450f6dcd5a8aaff1f21d68499e1b3cdca45aa83fe78fc6229edfd3514a2a`。S0 交接证明为 `f59023785bc7888806ea053015c30d43ecee27cc7046a211867d9daeb2e878b3`，中间证明为 `42d0eb64846943c440f6f468aceea55f56af264701bcb226c037d39dd852960d`。本机路径在原生消息提供；不要执行会写回原目录的 worker 辅助脚本。

## 独立审查内容

1. 核对新增范围、364 份不变基线和逐字节 S0 配置 `5aad6ff6db68ee4fe9bac0aa6104eaeff17bf948b509bfce3d14e3eac9d9aa29`。`training_authorized=false`、默认无训练开关、固定原数据/选择/协议身份必须保持；不接受由数据配置触发的导入、callback、代码或测试集 loader。
2. 审查 prepare 的完整原 verifier 调用、四个 train/validation 视图、原 Example/sidecar 隔离、完整数量/身份/rank 顺序和最小 padding 桶。核对 smoke1600/197、formal6013/217。用原创小例验证缺失/重复/错序/错误 profile/split/hash/audit/桶，以及固定输入/输出篡改失败。原 selection 仅只读 verify，不重新物化；最终 test/ood_test/BFCL 不成为训练或调参输入。
3. 审查实际新 collator 如何使用已验收共用 Sequence/pad_sequence 和绑定 tokenizer。直接核对原 13 例的完整输入/输出/原 sidecar 与新旧数组；可从现存原完整 token IDs 构造共用 Sequence 复核 shift、padding、EOS 与分母，不再对真实 13 例新增 tokenizer 编码，也不重跑 8228 行。针对原创小数据独立验证 prompt/padding 不计监督、P−1/N−2 和恰好一次追加 EOS；协议例仍单列，不能进入真实视图。
4. 核对 epoch 计划对 0/1/7/8/9/13/1600/6013 的处理，微步等权平均、完整周期与实际余数分母、顺序/覆盖、不补齐复制、不丢尾、不重置 model/optimizer/RNG 的设计；200/752 是计划。纯结构测试或 mock 不能关闭实际原生更新门槛。
5. 检查 ValidationTotals、Score、参数内容 hash 与选择器的作用边界：总 CE/总监督 token、完整 validation 身份、NaN/Inf/零分母/遗漏/重复拒绝、最小 finite CE/较早步/checkpoint hash。审查可选 post_update_score 对实际参数、文件、计数和状态的绑定设计，同时明确本次未跑 actual evaluate、尾更新和 checkpoint 保存重载；不得把人工构造 Score 的测试写成真实 checkpoint 验收。
6. 逐条核对两次原数值失败、源码与报告。`96fcbe1` 是 DLPack 探针错误；`9e71552` 的原 MLX-LM train 在 CPU 默认设备元数据处报 KeyError，尚未进入训练循环。确认代码/源码 hash、CPU 设备与 stream、租约生命周期、300 秒/4GiB上限、真实进程回收和原日志。现有已验收 P01 wired-limit 保护器保持原样；不能修改 vendor、伪造 API 返回值或切换 GPU 默认设备来跨过入口。
7. 可以在**最多一次**新的 R1 自有、持租约 CPU 子进程中独立复核原创小输入的 loss/gradient/padding/EOS/ignored-logits，并用真实有效模型/optimizer/dataset 参数确认原入口反例。限 13 条、每条 ≤16 token、词表 ≤16、参数 ≤4096、float32 atol=2e−6；只读复用原已锁 replay 环境。先取得共享租约，再设置 MLX CPU 默认设备和 Torch CPU/最多2线程，随后才建小数组；保留实际设备、全数值和原异常记录。训练入口负结果不需要循环重试。不得通过独立实现训练循环或手动模型更新冒充 actual MLX-LM train；无真实数据优化或额外 checkpoint 产出许可。若探针出现不同结果，完整记录并报告，不扩大执行范围。
8. 独立运行精确候选的适用 CPU 全回归与新语义探针。T1 四组为 895/2 skipped＋60＋2＋13=970/2，其中新 51 已在 895 内；110 subtests 和安装重复不增加独立测试数。保留真实完整 argv/UTC/环境/退出码/日志、skip 原因及全部失败；不改全局收集或原测试来获得通过。
9. 核对实际新 sdist 的118份Git输入＋PKG-INFO、默认及显式sdist重建wheel的57份包文件＋5metadata、全RECORD/公开内容边界、依赖不变和eefc142→最终33d的真实字节映射。新默认wheel在R1新target中进行必要的独立默认入口/原创小例/拒绝场景测试，核对8个新增模块的实际origin；基础依赖只读复用、可选库不导入。区分已有归档解析、新构建、新安装和NOT_RUN路线，不靠源码cwd或旧wheel证明新包。是否额外构建按证据需要决定；本包不要求为重复相同已绑定字节而机械重建全部制品。

Ruff、4 契约冻结、公开内容扫描通过；报告中的实际执行和未执行范围可单独复核。新问题给出精确、最小、可复现的证据，先完成独立审查，不替 T1 修复或重开旧 P01/P03 整包。

## 结论、人工与资源

按协议给出 PASS/FAIL/BLOCKED 和 P0/P1/P2，并分别说明**可用的 CPU 准备功能**与**完整原生 trainer 路径**的结论。已知入口阻塞不能让 CPU 功能审查省略，也不能因 CPU 功能通过而改写尾周期/checkpoint 的 NOT_RUN。若认为 CPU 部分可独立集成，应说明可用入口、已核对边界与仍不可依赖的接口；最终接收与兼容修订由 S0 决定。

原 100 行语义与 13 行 token/mask 人工表只允许 kris 填本人字段；原 HTML/JSON/身份列不变，合法填写不能自动判成原证据损坏。R1 不代签，不进行实际页面导航；原浏览器拒绝保持，不换浏览器/localhost/代理等绕过。实际页面与两项人审仍 PENDING，G-DATA、P04 正式训练和真实模型容量未授权。

除第7项受限原创 CPU 数值复核外不加载模型框架。该项每进程墙钟 ≤300 秒、RSS ≤4GiB，取得已有共享 OS 租约后执行；失败/超限停止并 wait/reap 自有进程，保留终态和释放证明。纯 CPU 测试可复用已有基础/纯tokenizer环境，用 -B/PYTHONDONTWRITEBYTECODE=1；basetemp 使用新的系统临时目录，不改变原测试前提。禁止新环境/依赖/权重下载、GPU tensor、真实模型/真实 P02 优化、BFCL、tracker、费用、公网服务或上传。

完成审查文件/原始证据索引/交接并普通推送新 review 分支后结束本轮，等待 S0。给出精确 candidate/review commit/parents/tree、源码和归档身份、真实命令、全部失败/跳过/NOT_RUN及资源清理；独立审查不自动关闭最终 CI/main 验证、人工门槛或完整 P00–P09。
