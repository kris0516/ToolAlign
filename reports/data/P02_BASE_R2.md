# P02 第二次公共基线同步

2026-09-06；D1；work/p02-data。**数据实现、原始两遍产物及人审输入完全未变；新公共基线的当前适用CPU、归档和隔离安装检查通过。** 本轮只完成基线同步与技术自测，P02独立R1/kris质量门仍待审。

S0发布的生产base为 `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`，本轮授权为 `f2a271be616cdb53c01e8d671029f31ae140c037`。从原完整候选 `46f546504f73588caa2e71aac316c3c312306df6` 非强制merge，形成精确受测提交 **`9bbd7d732cb9f84be2f1ca065beed9c9178801bc`**；父提交依次为46f5465与f2a271be，无冲突。未reset/rebase或丢弃原候选。

最终完整待审候选是本报告/新交接所在的后续证据提交，精确SHA由原生消息交付S0。该证据提交仅新增本报告、[机器证据](P02_BASE_R2.json)和 [P02-base-r2交接](../../coordination/handoffs/P02-base-r2.md)，不改变已测生产树或归档输入。

## 实际验证范围

当前实际CPU为 **298 passed，无skip**：仓库tests180项（含17项固定真实tokenizer），P00首轮46项、P00-r2 72项。默认核心环境另为163 passed / 17个真实tokenizer明确skip。旧57项S0-SHARED-01结构快照原文件与原结果保留，不修改“唯一extra”等历史断言、不把它们算入当前通过数；本次不是旧355项结果的重述。

默认环境为12个distributions，tokenizer私有环境27个；两者均无Torch/MLX可用模块。uv.lock有93条解析记录，不等于默认安装93个包。没有选择ML extra、导入模型后端或运行GPU校准。

| 命令/校验 | 退出码 | 原始日志 SHA-256 |
|---|---:|---|
| uv sync --locked --python 3.14 | 0 | `bb8bc16f1dca49f1c920035479617ececc4c881448a08d777e1a140c44bc35e1` |
| 默认核心pytest | 0 | `5d7b3b55b0a7ff1d0b3e8c552e5af1f2b6d51e847e1b6a93ad30901bf8a8a556` |
| 实际tokenizer环境，298项CPU | 0 | `900f507dcbea077dd1fef513ff350e8c1609476d943e05758992f23cd1f96ef8` |
| 当前check_source_distribution.py | 0 | `ed29958888158ebbdb90bbb15eac534d34468e439fe55497e0f7e941d5c875ab` |
| 原R1-r3补充边界脚本原样执行 | 0 | `b84e255ba28081a6556b77f2fee85652c734f564ced6e06cbf615ab87161a37b` |
| 当前正常uv build（sdist→wheel） | 0 | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| P00隔离安装与五类CLI fixture | 0 | `f116a443c64367b8688e49c72243b21917169f1af8c7e208d2acb85d4d9b8047` |
| 实际归档成员/原生产模块字节核对 | 0 | `2e52810f7553bd2b664df67d853f365acbcd9e70f27d974ba82e28ebe4ad5885` |
| 合并后数据/人审输入/旧交接保持核对 | 0 | `4b6ce947b96eefd26b6669d43914c5e47f03471caa69eeb4c1a2435eb5d2faec` |
| ruff | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| 冻结契约四文件 | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |

精确argv、起始UTC、耗时、退出码与log hash均在机器证据。公开扫描在完整证据暂存后执行，结果另附。所有本轮命令均实际执行，不把S0的main测试当作本worktree自测。

## 归档与安装

接入修复后才恢复默认源码包构建。实际sdist为135,139bytes，60个文件，SHA-256 `d7ee2db8d9ce257db9a035adbee389316f4a89d91832494117336e859c84a241`；除了生成的PKG-INFO，全部成员是Git追踪文件且字节相同，无链接或未追踪载荷。实际wheel为51,140bytes，29个文件，SHA-256 `78ad37239a3d1023295d2e7a73be19583bcd335a8f50b47ca1cefb61f86b4672`；24个源码/资源逐项与仓库一致，其余5个仅为dist-info。11个data模块在两个包中均与原9be07a5数据manifest中的module hashes一致。

当前App合成worktree脚本对sdist、由sdist重建wheel、直接wheel检查241个私有canary全部排除、18个公开对照保留。原R1-r3补充脚本覆盖45个私有输入和21个公开对照，三路均通过；这些集合有重叠，不能相加成覆盖率。

原P00隔离安装脚本在临时Python3.14.7环境实际导出并按hash安装默认CPU依赖、安装新wheel、验证依赖闭包/冻结schema/五类CLI fixture/脱离源码导入及无ML后端，全通过。旧失败sdist保持私有隔离且hash未变，原旧wheel也移入私有证据目录保存；未上传任何归档。

## 数据、人审与长度限制保持

与46f5465相比，src/toolalign/data、tests/data、data/manifests及旧P02-r1交接均未改变。合并前后分别重新读取policy-a/b的18项实际文件和根manifest，全部与原交接一致；本轮数据build运行次数为0。

- canonical build manifest：`87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`。
- 根manifest文件SHA：`c728dfe385e340fadf1e5949976c012709fc10a1dbca9010548edf74785259e5`。
- 人审HTML：`6193aa5da4a5dd4a5293472dd424ed1839e954d79d8d79afe524cd830b1dea8a`。
- samples.jsonl：`d8a608ba59fa375762aca65412f76fbef29046897b9e546c359bdccc3de62033`。
- 人审manifest：`cf82d8f9a5848c3cae0069d27a7549f385aabfdc4586a5de343795795883162c`。
- 冻结review.csv与当前填写副本文件SHA均为 `eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`。
- 100行不可变身份列（source_index/source_record_hash/example_ids/strata）canonical hash：`b7878f5ced14bdaa69f4cbbbffef177e2912625a411858e348cfef6b9b91590c`。

有效审阅包仍为100个不同来源、114个有效决策；填写副本的reviewer/verdict仍全空。本轮未更改抽样、有效数据或判定内容，浏览器渲染仍NOT_VERIFIED，由S0接手展示。准确本机入口由S0私有映射及本轮原生交接给出，旧零strict包不作为入口。

原数据总量8,228，数据build上限仍8192。按S0给出的P01上限2048，8,115例在窗口内、113例超过2048且≤4096；这些限制与原样本保持，不替P04截断、筛选、改组或决策。共享包通过不构成P02/G-DATA通过，也不授权P04训练。

本轮无失败；磁盘记录1,191,376KiB（约1.136GiB），低于5GiB。R1对P02独立审查、kris真实语义审查、P02 main集成、模型/训练/GPU/公开上传均NOT_RUN。交付后等待S0/R1反馈。

最终证据暂存后的公开扫描退出0，日志SHA-256 `3fa20bfcc1706e4230b9c04ee7b2a80a19ea30f0015c5406775ea4c8da5af449`。原始输出：PASS: 167 paths scanned in index and working tree; heuristic check, not a privacy guarantee。
