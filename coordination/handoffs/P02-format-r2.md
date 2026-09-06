# P02-format-r2｜正式实现交接

2026-09-06，D1 / `work/p02-data` / gpt-6-astra / max。状态 **READY_FOR_REVIEW**；保留独立任务和原 worktree。最终完整候选 SHA 以包含本交接的同轮原生回报为准；本交接引用的被测完整代码候选为 `9f4e7a3f699a9d6cd9e444da2dc18f35f2cc9207`，其父 `0e64d2d345fb5e9758dd0a9c5902cc2894a0cb23`。所有测量/包内源码在后续证据提交保持逐字节身份；独立 R1/S0 新格式验收尚未执行。

原授权 `0c94ad58a78d30cd88a9ad86ac8e8d8c83b2442c`；后续 P03 同轮同步 `5212b24c0ef2d5442e190ed791a9b7008d8e0724`。原6c3d330与0c94普通merge为88733d1；实现/唯一全量测量 `b33a55fba61d39f9da3c224ae6743c7cf6328cf6` 与5212普通merge为 `e086e1d1ece65fe2516b3992e1195ec61b4e5732`（两个完整父SHA均在报告），再增加公开包/边界probe及修正测试。原失败提交与全部父提交保留。

本轮只新增 `src/toolalign/model_io/`、`tests/model_io/`、`reports/data/P02_FORMAT_V1*`、本交接、新 `data/manifests/model-io-sequences.v1.json`。217个既有受保护公共路径匹配授权来源；原11data模块、两构建各18制品、100来源/114决策人审、填写副本和原3份提案保持。没有模型/GPU/训练、筛选/截断/改标签或人工判定。

- 纯入口独立验证 ModelInput，完整 Action 与 prompt 分离；包资源精确匹配 S0 descriptor，原 LocalTokenizer 不变。合法历史调用保持冻结规则自由，完整目标由真实 Example 验证。版本 `toolalign.action-json.qwen3-message-roles.v1`。
- 同12原创/公开fixture在 tokenizers0.22.2 与真实 Transformers5.16.1/tokenizers0.23.2逐项比较完整P/C/IDs/EOS/mask，独立恢复和小集重复均一致；两个同字节模型来源身份已绑定，未运行模型。
- 唯一全量8228行，序列错误0、parser和输入恢复精确8228/8228。总长>2048为1351，C含EOS>256为269，两项合格6685仅作统计；完整分母保留，不是训练集合。P50/P90/P95/P99、raw复杂度、全部split/预算/失败字段见manifest。
- 原私有P03副本与已合并parser都是`15f67a014fc1f2a044b8a180f425ab2cde1d668939c55a96d937e4a23373211b`。合并后直接parser另过同12原C；实际源码、格式、输入绑定不变，未再运行全量tokenizer。
- 最终组合 **664 passed / 0 skipped**，log `ab8992181072396d51b1a8e356e6eae93d595871cb730c297697fb1fcd790bd1`；真实tokenizer回归包含在内，lint与4项冻结通过。新合法Action超raw bytes/nodes/depth反例保持原parser拒绝。
- 实际sdist/default wheel/显式sdist重建wheel逐字节核对；默认wheel来自sdist，直接源码wheel NOT_RUN。87/44/44成员，默认和rebuilt wheel同SHA `a0aac74f1667ff860c850f96fd210acef02818187e7a80fbed869640d88b13ea`。10条隔离安装命令全0，39安装源码/资源、12样例新接口与原parser通过；无源码路径导入或模型/optional包。摘要 `a87fb5ef6090b2bf4c8a5ee7dcec75ef4baf9b746146012887725b2129882827`。

详细[实现与验证报告](../../reports/data/P02_FORMAT_V1_VERIFICATION.md)、[所有命令/制品去敏索引](../../reports/data/P02_FORMAT_V1_EVIDENCE.json)、[新序列manifest](../../data/manifests/model-io-sequences.v1.json)。公开manifest SHA `69bfa651bf8db9b2c77c11c4f8d55419a8af4196aba8ff6a69b5b3b0982e0f47`，私有逐例文件 `36b8cbfe6773c08f7a28521a99ed8783723a8f7fa3b2a3fa87915d8d1d871aff`，私有测量manifest `07daedb35169d6fa4d6eae1c7663387380035971c15c88ae5461ff4e7f617d23`。私有位置与最终SHA通过原生交接提供S0，不写入公共文档。

保留的开发失败：新测试import顺序；包probe漏列追踪.gitignore；rawprobe首轮误预期原parser未包装的错误。前两项只改测试/探针，raw断言修正记录在9f4e7a3，原失败log/源码/提交未删除。公开扫描最终退出0、235路径，log `1a9b666545d97f29026afcdf72071d5301ed84f580992cb49a115737c04c546e`。所有本轮完整日志hash及命令退出码见索引；最终测试无残留失败。

末次制品核对可枚举新增私有文件/日志/新pyc `33098412` bytes，预算2GiB；短命临时目录已清理，不把留存数字冒称精确累计。未创建新tokenizer环境，所有包命令离线；默认隔离安装使用新target目录及已有Python -I -S。原人审填写副本SHA `eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`，0 verdict/0 reviewer。

交接后只普通可快进推送当前工作分支，结束该轮等待R1。P04/P05/P06、训练选择、G-DATA本人语义审查、真实模型对格式的遵守、至少10条token/mask人工检查及trainer padding/packing/梯度仍未授权或未验收；本轮CPU证据不代签这些门槛。
