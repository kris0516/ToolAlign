# P02｜独立技术审查 r1 交接

reviewer：R1；日期：2026-09-06；分支：`review/p02-r1`；结论：**PASS（技术范围）**。P0：**0**，P1：**0**，P2：**0**。**P02/G-DATA 仍待 kris 真实语义审查与后续集成，不是 VERIFIED。**

完整被审候选为 **`b0d8d83750c48cd951c16b50cfa28a7898976e72`**。R1 授权 `c44739ac1e2fe282f5f51f80c5ea099687051ff3`；生产 base `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`；同步授权 `f2a271be616cdb53c01e8d671029f31ae140c037`；D1 受测 merge `9bbd7d732cb9f84be2f1ca065beed9c9178801bc`。R1 审查 commit 为本交接所在提交，完整 SHA 随原生消息交 S0。

已读授权 AGENTS、P02 任务包、PROTOCOL、PROJECT_STATUS、GOAL、数据治理/冻结契约/来源政策及完整实现、测试、manifest 和报告。契约为 `plan-v0.1` / `coordination.v1` / `toolalign.contracts.v1`。实际审查相对 f2a271b 的全部 **40 个 P02 文件**，包括旧数据实现；不是只复核 P02-base-r2。候选 167 个追踪文件逐字节未变，当前 11 个数据模块与实际构建提交 `9be07a5b88d1dac1a6e1fea30358af1049b1119a` 的 manifest hash 一致。

**独立证据。** 当前 CPU **298 passed / 0 skipped**，含 17 个真实 tokenizer 测试；另有 R1 新增 **40 passed** 原创反例。默认核心另为 163 passed / 17 明确 skip，不与前者重复计数。R1 使用自己的固定 27 包 CPU tokenizer 环境，没有启动 D1 环境、Torch/MLX 或 GPU。

R1 产物审计不导入 D1 parser/policy/grouping/tokenizer，实现独立分隔符扫描和严格 JSON 解码；仅复用冻结 P00 验证器。两边 18 个实际 artifact 一致；16,650 个工具、5,282 个 typed defaults、每项字段 before/after 和四种转换分母核对通过。8,228 个 example 的 15,073 个目标调用、632 个历史调用和完整输入前缀均从原始来源重建一致，比较保留数值类型；全部 7,662 个有效来源的所有调用均通过新增约束，含其后续调用。未补填默认值、强转参数、删除用户消息、泄入目标/未来 observation 或执行源工具。

原分组 3,517、最大组 6,716 保持，assignment hash 与旧严格检查点相同。规范化 schema 审计独立重算 11 个跨旧组键、4 个跨 split 键、64 个相关来源；全部相关来源隔离，最终检查键跨 split 交集 0。33 个完全重复排除项从源文本重建后确与保留项相同。数量闭合为 **13,819 = 5,505 + 8,314；8,314 = 53 + 33 + 8,228**；最终 split 为 **7,515 / 234 / 215 / 264**。LSH 不作穷尽语义等价承诺。

独立重新渲染/分词 **226 条真实决策**，包含人工包全部 114 条与全部 113 条超 2048 的样本（重叠 1 条）；整体编码、稳定前缀、额外一个 EOS 和 sequence hash 均匹配。P02 数据长度口径为 `qwen3_non_thinking_concat_one_eos_v1`，未 padding；raw 来源长度分开记录。**8,115 条≤2048，113 条在2049–4096**。P02 max_tokens=8192 不授权超出 P01 的训练窗口；P04 仍须绑定 manifest 并明确处理长样本。

来源锁的实际 data/README/tokenizer/LICENSE 与官方固定 revision/hash 对应；已保存的 API/access hash、当时非 gated 和许可标记核实。49 份 worker 原始日志及对应元数据、两次实际构建的不同命令/UTC/耗时/退出码均核对，另核对两份早期失败日志 hash。历史零 strict 和失败事实保留；新一次 web API 查验被 URL 政策拒绝，没有绕过或称为新联网确认。此前失败的私有内容 sdist 和详细失败日志没有读取或解包。

新的正常 sdist→wheel、实际成员及 P00 隔离安装/五类 CLI fixture/无 ML 检查通过。sdist **135,139 bytes / 60 文件**，SHA `d7ee2db8d9ce257db9a035adbee389316f4a89d91832494117336e859c84a241`；wheel **51,140 bytes / 29 文件**，SHA `78ad37239a3d1023295d2e7a73be19583bcd335a8f50b47ca1cefb61f86b4672`。当前 241 私有 canary / 18 公开对照的归档检查通过；不把合成检查替代真实正常包证据。

**人审交接。** 100 个不同最终有效来源 / 114 决策 / 34 分层、抽样算法、身份列、数据/lineage 对应及 500 个 HTML 内容区全部核对。冻结表和填写副本仍全空；身份 hash `b7878f5ced14bdaa69f4cbbbffef177e2912625a411858e348cfef6b9b91590c`，CSV hash `eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`。accepted_examples_reviewed=0、mislabel_rate=null，未替 kris 填判定。P05 的偏好对抽检规则不视为本次 P02 已验收。

R1 已通过仅绑定本机回环地址的临时页面，在浏览器实际观察说明与展开样本，确认换行和无横向溢出；DOM 为 100 样本区、500 内容区、0 脚本/外部资源。原 HTML SHA `6193aa5da4a5dd4a5293472dd424ed1839e954d79d8d79afe524cd830b1dea8a` 未变，页面和临时服务器已关闭。此项将“R1 浏览器检查”记为实际完成，保留 D1 当时未验证的历史报告。没有把单个视口观察说成逐页人审。

具体人工待决点：来源索引 **61**，hash `01934139e5914ea2edf537f242acf4fa1b266fc0295241e682f9245f0e8648fc`，原 turn **5**；该中间工具调用接在谈话性评论之后，需要 kris 判断是否符合当时意图。R1 确认原始目标与转换一致，未判定为转换 bug，也未填写误标或通过。这不是 P0/P1/P2 实现缺陷结论。

**日志与失败。** 全部实际 argv/UTC/退出码/完整 log hash 及复现说明见 [完整报告](../../reports/review/P02/README.md) 和 [机器证据](../../reports/review/P02/evidence.json)。核心日志：

| 检查 | 退出码 | 原始日志 SHA-256 |
|---|---:|---|
| 298 项含真实 tokenizer CPU | 0 | `a779b841d89a47c095c6de0ec44d00ae401f7a0e0a17aa97c0bdc3a411e62c76` |
| 40 项 R1 原创反例 | 0 | `2ab79feebcb72c3b3eb8a53d5d7916cd834c221a2e7c943c0de5cfd7d3b4d20e` |
| 最终独立实际产物审计 | 0 | `aa3621dc2f795a081b6c037786c138b4792a277b8f61491ca6f8725e480c59aa` |
| 来源/运行/环境/归档元数据 | 0 | `82da584ddaa9a86b54230c61124229be89a143b171716634af92b269fa72a3a3` |
| 正常 uv build | 0 | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| P00 隔离 wheel 安装 | 0 | `f116a443c64367b8688e49c72243b21917169f1af8c7e208d2acb85d4d9b8047` |

R1 三次准备阶段非零分别为旧测试文件名错误（exit 4，无测试运行）、新增反例的一处引号错误（exit 2）、首版审计把 HTML JSON 对象显示顺序当成内容差异（exit 1）。只修正 R1 新增代码/调用，随后通过；初始脚本与日志保留。临时预览服务器的 interrupt/130 为主动结束。候选实现没有被修到测试通过。

新增私有环境/缓存/证据约 **77.4 MiB**，另约 182 KiB 新包，低于 2 GiB。仅新增本交接和 `reports/review/P02/` 的报告、证据及三个独立探针；旧候选、旧审查分支、历史失败证据保留。

最终公开扫描退出 0，检查 173 个 index/worktree 路径，日志 SHA `a1b028a00bc5b0948702a13c571a0891f2b2e9b47dce209eda98bb9c6c427603`；最终范围核对退出 0，确认仅 6 个允许的新文件、167 个候选文件和两份空人审表未变，日志 SHA `f64a971d66471d84d535a63dfaeefb7b003b438260b9c136752b89850b481252`。启发式公开扫描不等同于普遍隐私保证。

**决议与 NOT_RUN。** 本技术 PASS 可交 S0 继续精确候选的 CI/集成流程；P02/G-DATA 仍待人工。NOT_RUN：kris 语义验收、训练 manifest/窗口绑定、增强/偏好挖掘/SFT/DPO/正式评测/BFCL/推理服务、模型或数据上传、P01/P03 整包、两遍全量数据重新 build、HF 参考环境重新安装/执行、旧严格包 14 文件重审、此前失败私有归档/详细日志、新联网来源确认、最终 GitHub CI/main 合并及集成验证。无需 D1 改实现来关闭本轮问题；S0 安排后续门，R1 提交并回报后停止等待。
