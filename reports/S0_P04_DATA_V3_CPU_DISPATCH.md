# S0｜P04 v3 数据与固定数组 CPU 适配准备

状态：**IN_PROGRESS，已原生派发并核验 ACTIVE**。2026-09-07 17:39:24 UTC 完成输入冻结。[任务](../coordination/tasks/P04_SFT_DATA_V3_CPU.md)由原独立 T1 承接，gpt-6-astra/max，新分支 `codex/p04-sft-data-v3-cpu-r1`。code_base `48be4352bbad53ced5af84186edac036dd0ff2ca` 已包含 PR15 技术主干、原 R1/Q1 审核和 S0 G-DATA 批准，生产源码保持已验证 `90c4da99f093b846a6b0ca0343d8293739ce2bea` 的字节；完整授权提交在实际派发时登记。

目标是从已验收 v3 的四个选择集合建立不可变 SFT view，再将 13 份已审阅完整数组转换为现有 Batch，导出/回读并逐位置检查。只读 verifier、旧 collator/plan、默认 CLI、toy 守卫和契约保持。源与安装版各限一次固定 prepare、一次完整 13 例转换/导出/回读；不新增 tokenizer/renderer/decoder 调用、数据 build、框架、模型或优化。计划仍是 smoke 198 更新（尾 7）和 formal 743 更新（尾 2），实际更新 0。

[S0 精确配置](../configs/sft-data-v3.v1.json) SHA `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1`；固定输入 manifest `08e865ff98bd476c94153033bc192664d72cee64443184576532c0289a610dd7`。609 成员中 603 只读引用/6 精确副本，副本 320,921 bytes；原 D1 verifier 输入 348 项、v3 输出 30 项、Q1 输入定点子集 211 项、Q1 正式结果 10 项、其他批准/配置/R1/S0 记录 10 项。原文和绝对路径均只存本机；出处和旧 proof 内历史路径不构成递归读取授权。

数据批准 SHA `1edb1e889b91dbde5dc6208b8dff2afdaa4b4a20a0ba5c166e9b55750429ec44`，台账 `022356d8dc6fdf273804d0f78e58416677799e303b0dc1b6a46b1e7b1ffcb992`，R1 原 dbd11d0/Q1 原 7941 的精确结论与 seal 均已绑定。旧 candidate 中的 pending、旧编码时间和 training_authorized=false 保持；本包以新的 S0 批准为当前数据门证据。

T1 上一 4baa367 轮原生 completed/notLoaded、工作区干净；5,744 原接收路径、556 公开 Git/新快照、161 scope 文件和 197 原链接文本已核对。两个旧测试链接当前悬空，原 seal 未记录其旧目标存在性，且目标不在应保留文件集合中；保存原链接文本与当前观察。S0 首次辅助断言额外要求旧链接目标全部存在而失败，已保留脚本/原回执，未删除或重建旧目标。新消费输入仍拒绝 symlink。

T1 保全证明 `8644138a91d76281c4be89b87ef308c5431e4fde254bd8b509f99b025d30a259`；冻结总证明 `0526b064a3a606416edd7aa84e93bbb5ad4bc202824aa4951264e95350bcc492`，实际核对 6,357 路径，S0 新生产测试/编码/模型/框架/GPU均 0。后续须实际派发、核验新 identity/branch/intake、完整候选、R1 独立审查、最终 CI 和 main；本准备未提前登记实现成功。真实 trainer、容量、正式模型实验和浏览器实显仍 NOT_RUN，无新费用或外部发布。

实际派发：2026-09-07 17:45:52 UTC，S0再次核验T1旧轮completed/notLoaded及完整授权`0fa77e228021091e357505a0e81a5d3ba0777928`远端一致后，原生接续T1并显式使用gpt-6-astra/max。新轮ACTIVE已确认；新branch/identity/20授权副本/609输入的完整intake仍待T1交付，不提前登记实现结果或关闭后续审查门。
