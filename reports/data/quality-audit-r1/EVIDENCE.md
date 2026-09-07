# P02 quality-audit-r1｜复核证据

本轮实际内容提交为 `e5030e917e249eaa456f116b1b6490abae9c7e30`，parent 为采样器提交 `7298456d5b54361beed0df681964078bc200957a`，tree 为 `4c2f941b7c1b4545a52e4152165f3794fe1450f0`。本文件和交接单随后仅作文档提交；最终完整 SHA、parent/tree、公开检查与私有封存由原生交接按实际结果登记。本轮只作本地提交，没有 push。

日志中的 HEAD 是各命令实际执行时的 HEAD。初始 fixture 在基线 HEAD、两个尚未追踪的原创脚本上运行，精确脚本字节由采样器 worktree manifest 映射至 `7298456`。其后新增脚本在该 HEAD 的工作文件上执行，八份最终报告目录文件由 implementation worktree manifest 映射至 `e5030e9`，没有把后来提交冒写为先前运行 HEAD。两个 manifest 的 SHA 分别为私有原记录所载，以及 `9c2c3b355bfda1a8ec3166ea39234bd7d0bf67f9c8c354c74472dbf3f91638b3`。

| 实际检查 | exit | 结果 | 原始日志 SHA256 |
|---|---:|---|---|
| intake | 0 | 13 项输入绑定及 manifest canonical hash | `c185cdf9e60258ac54305476df83ae4a6b02a44b1acb127399723ea6bd611723` |
| sampler-fixtures | 0 | 12 项原创隔离/排名/不足池 fixture | `ba56007400fa5292f01fa84ee89753d8713c5eaf824f5bc044e66f837f4f6d17` |
| freeze-sample | 0 | 固定 32 + 180 来源、40 + 200 目标 | `02b5362e0d13eb0a32869eb171665df6f5d98e4a1a388b9008890ce8835546e2` |
| material-intake | 0 | 105 项原材料绑定，75 份私有副本 | `4f3b036b89524618a2873009f9ea36f0a81364602e46c25fe03fc02ebf3d20b5` |
| material-source-bindings | 0 | 10 原来源、11 个全部有效目标 | `faa06ec42c95626da6a5af2fa0b4778c374aa092708b0b5b4789ca0992718d32` |
| material-staging-identities | 0 | 两个直接草案和一个后继目标的精确差异 | `189cf24782ab7150229cb4f701f118f2294f19883a912253b97ee349c7897c0a` |
| material-token-mask 首次 | **1** | E1 检查器误假定旧 HTML 的独立 ModelInput 区块 | `e51fa1b2867ee731b90025c87edd5363ebe458ab5ba2c5a7a505dd5fa7075ed1` |
| material-token-mask-r2 | 0 | 按实际完整 Example 区块比对，16 份全部位置通过 | `a1f4d91bf37d45651105c626a2b49d354d9535e0021012a1ff9b7250ee3923f8` |
| material-fill-reviews | 0 | 写入本轮审阅副本，保持原身份列 | `bb3579bfcd318a15079ff14940f8b1ad12311936dc49cc2b8fd64d953090325a` |
| material-seal | 0 | 原材料、原空表、冻结 180 名单未变 | `64428aaaf89cccd040b450913352098deded272ed3092d3a3771f09e0fbfe1d2` |
| aggregate-reviews | 0 | 222 来源、251 目标、87 问题、1 advisory | `5e91ef2ea2cf4a04558337dc344579f6151e8429072b8017efb0586bc9ab0fdc` |
| semantic-view-reconstruction | 0 | 43 视图、628 原始 turn、660 累计前缀消息逐值相符 | `954a6e341563f5a4cbaa352ab62d64b8d848019e42b21c0b8a6aad3d3f5ff4c4` |
| delivery-lint | 0 | 本报告目录 Ruff | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| preservation-final | 0 | 4,441 个不同文件的封存/范围核对 | `dd0826c34713c90e2be0d8e9ebf9f54a2b3a0e049a9d4cf9a3f37f77c53f8ae8` |
| public-content-candidate | 0 | 436 路径 index 与 working tree 启发式扫描 | `60e284bc324ea890c92c4dfcdd384463a5dc5b321ba15ae367976ce709570f32` |

所有命令的完整 argv、真实 UTC、elapsed、exit、HEAD、index tree 和日志 hash 保存在本机原始检查记录；包含私有输入路径的命令不公开。初始 sampler-lint、审阅汇总前的 audit-ruff-final 也保留原记录，未代替或重复运行未变的生产测试。

首次材料检查失败仅因 E1 检查器的 HTML 区块假设错误。修改前检查器已保存，SHA 为 `343f197f11322b5edd8ad14fd5cb13cac4e4d80013e5ec04fb2ea3b810abaa73`；之后将该一处检查改为比对实际完整 Example，原 Sequence/padding/mask 断言全部保留。原 D1 材料不变，第一次失败日志不删除。辅助只读定位也曾因猜测文件名出现 exit1/2；显示截断的语义材料均在判定前补读完整。没有为未单独落盘的辅助读取伪造“原始日志 hash”。

保全核对包含 428 份基线追踪文件、3,235 件旧私有制品、13 项原始输入、21 项旧委托封存文件、追加 105 项原输入与 75 份私有副本，以及本轮各级样本/判断 seal；重复绑定只算一次不同文件。原三条工作/远端跟踪 refs 保持。精确输入、名单、group/split 与原审查字节不变。公开文件另与本批来源 hash、Example/group 标识及完整原句比对；启发式扫描不是全面隐私保证。该检查时新增私有制品为 28,979,268 bytes，最终交接另登记封存后的大小，额度为 1 GiB。

| 关键已封存结果 | SHA256 |
|---|---|
| 冻结新增与复核样本 manifest | `cfbfd97125b52ff60e7ae39db8127936a7a55bc6e8b0161244f27c055b0596d3` |
| 原 32 独立判断，读取旧说明之前 | `2797c582e90fc45a600bc0c94c98b63f9dd5419dc8cb44639025c009cd880046` |
| 原 32 对照 | `254a7af645df9c49b0ce789ff6effca1a8326bd20365deca99afdc0ff411ebdf` |
| 两草案审阅 | `dc1f56b8e6620cf9364a561684f43625bc66d6f6042e4206b20053f5ac92b9e6` |
| 新增 180 全部判断封存 | `1c5efbe8d9e04fe96c307a2fc46960ab513377b1e81d6dd28c205e7e0abeeea2` |
| 追加 16 材料封存 | `b180447fe591b2eb0dc677a24c129947789245564d0ac7c18a14d4ef86016622` |
| 汇总 review.csv，222 行 | `db7bd1852593d91a1f6f03ce83e48934cf302759c524451def3fa681047ca950` |
| decision-review.csv，251 行 | `dc2290fe93bd8db04fb4ece5e858f5fcf5d1a242320cc31a97cbe0bfa7c3d404` |
| issues.jsonl，87 条 | `edcf3d7e7ac980ed4447f1d6d4d2b723e10c76aa70eb448f0b7a5ff10e86cf37` |
| context-issues.jsonl，1 条 | `e801ed9af0d7d1297a2a4228c55a510f39d1f342f2fb1d9f773f540e458d62af` |
| prior-recheck.csv，32 行 | `a34071b53026bb503c4794351ddde6b297cf3551be54ff626aac46b578f2d589` |
| proposals.json，全部为建议 | `c09972301541657c5e45d5d6bd91496e39869acc2b19df31dffdc5e5f8d2b3d5` |
| traceability.json | `bc25423a29152d6c7112179f03f2eae932f7e90171dffac644f1d4c9b697ce88` |
| RESULTS.json / 私有 summary.json | `bfb1df200bd7e9d6d76fa16548f00f72bb8c9e8ac737296f55e8326950800c89` |

复现使用现有环境；以下路径变量为脱敏占位符，实际 argv 在私有日志。采样命令会输出私有原始来源，只能指定新的 gitignored 目录，不得覆盖既有封存。已验证的原始输入应按授权 hash 提供，不另行下载。

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q reports/data/quality-audit-r1/test_sampling.py
.venv/bin/python -B reports/data/quality-audit-r1/verify_semantic_views.py --audit-root "$AUDIT_PRIVATE_ROOT"
.venv/bin/python -B reports/data/quality-audit-r1/summarize_reviews.py --audit-root "$AUDIT_PRIVATE_ROOT" --output "$AUDIT_NEW_OUTPUT"
.venv/bin/ruff check reports/data/quality-audit-r1
.venv/bin/python -B scripts/check_public_content.py
```

`audit_sample.py` 的 `--config`、`--policy-root`、`--delegated-root`、`--raw-source`、`--output-root` 由冻结授权输入提供。`semantic_view.py` 输出完整 source、normalized 工具/消息/目标，并只按精确字符串或 JSON 值复用显示；`verify_semantic_views.py` 从已保存文本反向重建每个字段作独立比对。`summarize_reviews.py` 只读取已写定的人工逐条判断及独立补注，不能生成语义结论。`check_materials.py` 仅核对已经存在的封存材料，不加载 tokenizer 或模型。

新环境/依赖、下载、tokenizer/model runtime、GPU、真实 API、浏览器实际显示、训练、正式评测、BFCL、生产全套测试、生产包构建、候选 CI/main 集成与公开 push 均为 NOT_RUN。本轮没有待用户补填的人审步骤；后续由 S0 安排独立 AI 复核和精确整改。
