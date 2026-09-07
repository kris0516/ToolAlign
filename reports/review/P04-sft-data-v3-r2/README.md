# P04-SFT-DATA-V3-r2 独立复审

**FAIL；P0=0、P1=0、P2=1。** 精确候选 `1769046468eb2ebfdd9e982ba4938833760e3fe0` 的原 F1 无 writer FIFO 阻塞已经关闭；新增发现 **P04-SFT-DATA-V3-F2**：普通文件在预检查后被替换成目录时，`fdopen` 构造失败留下已打开的裸 FD。目录输入及时拒绝，但资源所有权未收尾，仍需修订。原 F1 的首次 FAIL、T1 旧消费失败及本轮补充检查的原失败均保留。

任务 `P04-SFT-DATA-V3-R2`，独立 Codex-AI(R1)，`gpt-6-astra / max`；分支 `codex/review-p04-sft-data-v3-r2`。候选 tree `1373bd4c838a1af395a1ede4f7c4d7029ffad271`、直接父 `53d86109f18e4131cff1ddcb905086892580d136`，再承接原 `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa`。完整授权 `1cb1b0a6ffc157edcb53b41f21cef883f4729d13`；契约 plan-v0.1、coordination.v1、toolalign.contracts.v1、ADR-0026 与 REVIEW_POLICY。只审本次 I/O 修订和正常消费回归；生产/测试/配置未由 R1 修改，也未合入新 main。

## P2：目录替换失败后裸 FD 未关闭

位置：[data_v3.py](../../../src/toolalign/training/sft/data_v3.py#L93) 的 `os.fdopen(os.open(...), "rb")`。

实际可达路径为：`_path` 与 `lstat` 看到普通文件 → 该叶路径在 `os.open` 前被替换成目录 → `os.open(O_RDONLY | O_NOFOLLOW | O_NONBLOCK)` 成功取得目录 FD → `os.fdopen` 抛出 `IsADirectoryError`。异常发生在 `with` 上下文建立之前，随后转换为 `v3_input_io_failure`，没有清理原 FD。

[补充检查](test_independent_io.py) 的目录分支原结果为 FAIL，不能写成六项全通过。另一次无 stream 包装的原创最小观察确认：拒绝后 **1 个 FD** 仍可 `fstat` 且指向目录；没有 writer，没有读取目录内容，没有调用真实数据 API。该观察随后主动关闭自己的 FD，确认 `EBADF`；先前失败子进程也已退出并回收。

严重度为 P2。当前消费者是一次性受限 CPU 进程，退出会释放本轮残留；但 `prepare_v3`/`_read` 本身没有限制长生命周期调用方捕获错误后重新尝试。裸整数 FD 没有对象析构清理，重复发生此替换可逐次累积，并最终导致 `EMFILE` 与其它 I/O 失败。**一次残留为实测；重复累积及耗尽为源码推论，循环耗尽试验 NOT_RUN。** 需要并发路径替换这一触发条件，当前固定正常输入没有触发该问题。

原 f3 中已有同样的嵌套构造失败路径；本轮仅只读对比其源码，未重跑旧候选。既有缺陷这一事实以及审查的一次调用额度均不构成降低严重度的依据。中间曾拟列非阻断限制，复核实际生产调用生命周期后已纠正为上述正式 P2；原中间回报与原失败仍保留。

建议由实现者显式拥有成功 `os.open` 返回的 FD：stream 构造失败时关闭它，构造成功后才把清理责任交给 stream。继续保留 `O_NOFOLLOW`、`O_NONBLOCK`、同 FD 的类型/hash/大小/预算检查和及时拒绝行为。R1 没有代改生产实现。

## 原 F1 与回归结果

| 已执行项目 | 结果 |
|---|---|
| 原未修改 FIFO probe，源码一次 / 新安装版一次 | 均 PASS；无 writer 即拒绝，原 1 秒观察上限未延长，两 child exit 0/reaped |
| 相关模块一次 | 147 passed / 0 failed；含 T1 新增 12 项，不累计旧轮计数 |
| 原创补充 I/O 检查一次 | 5 passed / 1 failed；FAIL 为上述目录 FD 残留 |
| FIFO / symlink 在 precheck 后替换 | 及时拒绝；FIFO 未读取 payload，成功打开的 FIFO FD 已关闭；无 writer |
| 正常 content / hash-only，打开后替换路径 | 仍对同一原 FD 校验并返回原字节；FD 收尾通过 |
| `fstat` 后文件增长 | byte-budget 拒绝并关闭 FD |
| 目录最小确认 | exit 0 表示观察完成，确认的是缺陷，不能计作生产行为 PASS |
| Ruff / 冻结契约 | PASS |

原 probe SHA `f44cc02cc066ad9f2befe1b11c27c92981ff77ae87cf83672c422e3118ff1c7d`，随本报告保留[原文件](probe_nonregular.py)。source / installed 证明分别为 `b28f618a5cdb80ad68e9e40de6e9bd49d01e5559b39107e2668b51526cbc23b5` / `255e48a7f078200c2edab9245f17b95d43899ab1a8167765ff518751151d99b7`。两次实际 child 都绑定本修订模块 SHA `212c688c1a38e4c2ce7863e34efc7635d75878729e4e141333caeb08a6fd16a4`。

F1 的原稳定要求是非普通输入在阻塞前拒绝及 precheck 后换 FIFO 不再等待 writer；两项已满足，建议单独关闭 F1。新 F2 的稳定要求为 stream 构造失败后关闭已成功打开的 FD。正式台账去重、计数与后续分发由 S0 处理；R1 未自行修改 counter 或整体目标状态。

## 新安装版固定消费

三归档完整核验通过：sdist 143 个普通成员，直接/rebuilt wheel 各 70；65 份包字节与精确 `53d8610` 源码及最终候选一致，METADATA、entry point、LICENSE 与全部 RECORD 核对。sdist SHA `cabbc8a37151f767925d9f83fd05b9adab93c88798db11fb298135b84b55d3de`；两 wheel SHA `101eccd619e16805230cfdb8b440d4f19858020ae5d6c1d3d4068b0d31fa1ecf`。26 条 T1 实际命令的 argv/UTC/exit、源码快照、完整日志与原生终态已绑定；保留 T1 recorder 启动前目录缺失失败和缺失的精确开始 UTC，不补造记录。

唯一一次离线 `--no-deps` 安装复用现有五个默认依赖；新 target 的 65 份包文件、75 行 RECORD 及另外单列的空 `.lock` 均核对。外部 cwd、`-B -I -S` 与显式默认依赖 resolver 下，32 个已加载 ToolAlign 模块均来自新 target，无源码回退。

固定输入 manifest `08e865ff98bd476c94153033bc192664d72cee64443184576532c0289a610dd7` 的 609 个成员、6 份副本/320,921 bytes 与配置 `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1` 不变。执行前冻结 consumer、完整输入、配置、预期 wire bytes 与 reservation。仅新安装 target 执行 `prepare_v3` 一次、13 例转换/导出/回读一组；实际 verify 一次、rebind/export/readback 各一次，无追加调用。

四 view 逐原行及 rank 共 7,928：smoke train/validation 1,583/194，formal 5,938/213；有效全集 7,419/230。与原 v1/v2/v3 行、Example/sidecar、group、来源处置、三代 rank 逐项一致，并与原 R1 完整 view 结果逐字相同。

13 个唯一例、两 engine 26 份完整记录逐字段/类型核对；完整 IDs、attention/loss/causal mask、shift、EOS、padding 和 token_texts 保持，原 Q1/producer/run/source epoch 绑定不变。11 例沿用原编码、2 例沿用原新版编码，3 个 protocol fixture 始终在训练 view 外。未重新编码、未构建全数据；最终 test/ood/BFCL 只 hash。

新导出 2,030,656 bytes、SHA `4c261560f3e27842d1cad0fce16220c8073df8a35a9592c4526c61f64a5a738c`，等于执行前冻结的预期。相对原 R1 导出 `9b711be1ba6b301e6efb8c9853c0c6b98fdaa2db9db2e2cd2fa348739ca6ba0b`，唯一变化是 `consumer.package_files.training/sft/data_v3.py`；所有其它字段与字节保持。新 consumer helper SHA `f4f900defda83f5a11efae7079ef72b26dbafd35150021b2e72c8360315b1d44`，新 source/input pins SHA `10275ca1b84af54f6245cc39d908dc77f09f4f6fd5adf942b63b0f7e39868aea`；原 T1 当前修订实数据 NOT_RUN 历史未被改写为这次独立消费。

## 证据保全与限制

切换前核对原模型 review `bdebe4c2bddf927995a6c15124fab75ad04ba5de` 的 90,443 文件路径、1,664 链接、4 个 lstat-only FIFO、628 公开 Git/快照字节与 23 原命令；完整旧 scope 960 文件保持。20 个原模型文件只核对 stat token，无新增读取/API。原 30 文件/1 链接缺失及等字节封存保持，不声称原件恢复。根 identity、所有旧 FAIL/PASS 与私有 f708 的公开祖先边界保持。

T1 本轮 intake 核对 13,320 路径、389 链接、4 个原 FIFO 节点、621 候选与 618 原基线、16 份 S0 授权、7 份原反例副本。全部原 FIFO 以 lstat 分类封存；测试自身非阻塞打开与封存不打开两件事实分开记录。新 pytest 使用两个独占根，均无 `.toolalign-local` 祖先；不清理旧临时根。

自身保留四次只读查找/显示辅助错误、一次 preservation 辅助脚本把映射误按计数判断的失败及修正后成功；未消耗数据/安装/probe 额度。首次预期 wire 字节准备缺尾 LF，在执行任何固定 API 之前按原 wire 格式纠正并保留草稿；本轮固定消费只有一次成功，没有失败重跑。补充目录测试原 FAIL 和严重度评估变更完整保留。

实际预算：安装 1、原 probe 源/安装各 1、固定 prepare 1、固定 13 例组 1，余额均 0；新归档/环境/依赖/下载、tokenizer/renderer/encoder/decoder、框架/tensor/模型/GPU/优化/生成、业务 API/浏览器/费用/上传均 0。新增制品上限 1 GiB，最终普通/链接/特殊节点清单与总量在 terminal seal 中封存。

完整 argv、UTC、exit、stdout/stderr、源码时点和私有材料留在本机，公开仅提供[去敏索引](verification.json)。提交前公开扫描、差异/允许路径与提交/普通推送回执另由终态 seal 绑定。审查提交以完整候选为直接父，只含本目录与交接单。由于 P2 仍开放，本候选不建议验收或主干集成；真实 trainer、容量、训练、正式评测和服务仍 NOT_RUN。
