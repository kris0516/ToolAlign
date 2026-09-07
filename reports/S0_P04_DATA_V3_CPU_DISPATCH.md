# S0｜P04 v3 数据与固定数组 CPU 适配准备

状态：**IN_PROGRESS，已原生派发并核验 ACTIVE**。2026-09-07 17:39:24 UTC 完成输入冻结。[任务](../coordination/tasks/P04_SFT_DATA_V3_CPU.md)由原独立 T1 承接，gpt-6-astra/max，新分支 `codex/p04-sft-data-v3-cpu-r1`。code_base `48be4352bbad53ced5af84186edac036dd0ff2ca` 已包含 PR15 技术主干、原 R1/Q1 审核和 S0 G-DATA 批准，生产源码保持已验证 `90c4da99f093b846a6b0ca0343d8293739ce2bea` 的字节；完整授权提交在实际派发时登记。

目标是从已验收 v3 的四个选择集合建立不可变 SFT view，再将 13 份已审阅完整数组转换为现有 Batch，导出/回读并逐位置检查。只读 verifier、旧 collator/plan、默认 CLI、toy 守卫和契约保持。源与安装版各限一次固定 prepare、一次完整 13 例转换/导出/回读；不新增 tokenizer/renderer/decoder 调用、数据 build、框架、模型或优化。计划仍是 smoke 198 更新（尾 7）和 formal 743 更新（尾 2），实际更新 0。

[S0 精确配置](../configs/sft-data-v3.v1.json) SHA `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1`；固定输入 manifest `08e865ff98bd476c94153033bc192664d72cee64443184576532c0289a610dd7`。609 成员中 603 只读引用/6 精确副本，副本 320,921 bytes；原 D1 verifier 输入 348 项、v3 输出 30 项、Q1 输入定点子集 211 项、Q1 正式结果 10 项、其他批准/配置/R1/S0 记录 10 项。原文和绝对路径均只存本机；出处和旧 proof 内历史路径不构成递归读取授权。

数据批准 SHA `1edb1e889b91dbde5dc6208b8dff2afdaa4b4a20a0ba5c166e9b55750429ec44`，台账 `022356d8dc6fdf273804d0f78e58416677799e303b0dc1b6a46b1e7b1ffcb992`，R1 原 dbd11d0/Q1 原 7941 的精确结论与 seal 均已绑定。旧 candidate 中的 pending、旧编码时间和 training_authorized=false 保持；本包以新的 S0 批准为当前数据门证据。

T1 上一 4baa367 轮原生 completed/notLoaded、工作区干净；5,744 原接收路径、556 公开 Git/新快照、161 scope 文件和 197 原链接文本已核对。两个旧测试链接当前悬空，原 seal 未记录其旧目标存在性，且目标不在应保留文件集合中；保存原链接文本与当前观察。S0 首次辅助断言额外要求旧链接目标全部存在而失败，已保留脚本/原回执，未删除或重建旧目标。新消费输入仍拒绝 symlink。

T1 保全证明 `8644138a91d76281c4be89b87ef308c5431e4fde254bd8b509f99b025d30a259`；冻结总证明 `0526b064a3a606416edd7aa84e93bbb5ad4bc202824aa4951264e95350bcc492`，实际核对 6,357 路径，S0 新生产测试/编码/模型/框架/GPU均 0。后续须实际派发、核验新 identity/branch/intake、完整候选、R1 独立审查、最终 CI 和 main；本准备未提前登记实现成功。真实 trainer、容量、正式模型实验和浏览器实显仍 NOT_RUN，无新费用或外部发布。

实际派发：2026-09-07 17:45:52 UTC，S0再次核验T1旧轮completed/notLoaded及完整授权`0fa77e228021091e357505a0e81a5d3ba0777928`远端一致后，原生接续T1并显式使用gpt-6-astra/max。新轮ACTIVE已确认；新branch/identity/20授权副本/609输入的完整intake仍待T1交付，不提前登记实现结果或关闭后续审查门。

完整 intake：2026-09-07 17:55:20 UTC，S0 直接核对实际新分支 `codex/p04-sft-data-v3-cpu-r1` 与精确 48be435、612 基线文件、20 授权副本、609 输入、新原生身份及旧 Git/封存，7,010 当前路径通过，证明 `e6d4c83e9ee050c449c030e0b848b46d62b7cf4ebd0f03e0ae6e30e5dd368d2f`。197 原链接文本和两个原悬空状态保持；原三个 worker receipt 皆 exit 0，其原生 argv 交叉绑定留至完整交接。本次 S0 实际数据 prepare/转换/编码/框架均 0。T1 继续同一 CPU 实现；[独立 R1 范围](../coordination/tasks/P04_SFT_DATA_V3_REVIEW.md)已 PLANNED，待完整 candidate/原生终态后冻结和派发。


CPU中间修复与复测范围（2026-09-07）：原source尝试18:25:48–18:25:49 UTC在D1祖先路径绑定处失败；原installed尝试18:34:43–18:34:44 UTC在Q1混合seal的`relative_path`处失败。两次均早于实际quality_exclusion.verify及13例转换；source原helper未保存失败计数，未到达由原traceback/源码推定，installed保存的计数明确为prepare1、verify/转换/导出/回读0。旧失败、两保留记录、原三归档及旧target均保持。

T1提交checkpoint `bfdf2a256065d5396e6f7a4860fd7c7506f5c278`：90个明确固定的外部祖先成员按原kind/path/hash绑定；Q1 seal的private条目与3个public-at-commit条目分别验证，不跟随历史可变公共路径。当前新增模块135项CPU自测通过；原常规组758通过/3临时目录假设失败保留，仅更换临时目录后原3项通过，旧测试字节不改。S0只读核验373路径/12原命令与源码快照，证明 `e8668110c9412d3bc5d1015a38efc2d7ea94b9ec48b1d106ed759b80642b50d0`；未运行S0生产消费/build/install。旧source-only请求在源码随后变化时被S0校验拒绝，原辅助失败保持，没有产生旧请求批准。

[本轮精确CPU批准](../coordination/approvals/P04_DATA_V3_PREPARE_RETRY_R2.json)仅准source/installed各新一次只读prepare及原未使用的各一次13例转换/导出/回读，旧失败计入总prepare各2。为安装版按当前源码做一次新三归档和新target，全部用新私有路径。完整candidate/R1/最终CI/main与实际模型路径仍待完成；本次135为T1自测，不作为S0独立审查结论。

18:51:22 UTC，T1已在新路径完成修订后的三归档和default target，S0核对226路径、原5条构建/安装命令、70/70/143归档成员及65份包文件字节，证明 `c2c8fcc68ede5e994d5060692c316abf997cb03faa9138b39a6f5514302287f7`。新direct/rebuilt wheel均8070c495，sdist be725d44；该一次重建额度已使用，本批准不再添加构建/安装调用。复测直接使用该固定新target，旧c7源码归档与失败仍保留。
