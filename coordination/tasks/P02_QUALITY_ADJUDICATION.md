# P02-QUALITY-ADJUDICATION｜采用独立裁定的新数据版本

状态：ACCEPTED（CPU技术）。完整1c47候选的原R1 PASS d5b8已由S0接收，原生空闲；PR14最终集成/CI/main和Q1完整质量结论仍待完成，见[接收证据](../../reports/S0_P02_QUALITY_V2_REVIEW_ACCEPTANCE.md)。以下原冻结授权保持。

- code_base：已验证PR12 main `6c81dfcc855fca188181d1bb08870f47d8edacc9`。
- 新branch：`codex/p02-quality-adjudication-r2`，仅自己的隔离worktree；原`work/p02-quality-remediation`的9b7cf01与旧产物保持，不pull/reset/rebase旧分支。
- 先从S0给出的完整authorization_commit读取本任务、配置、AGENTS、GOAL、PROTOCOL、REVIEW_POLICY、REVIEW_FAILURES、ADR-0024及最新接收报告并保存新私有副本，再从code_base新建分支。
- 契约：plan-v0.1 / coordination.v1 / toolalign.contracts.v1，当前Action JSON v1与旧规范不变；新身份仅写新scope，不覆盖旧根identity。

固定输入由S0私有分发词给出。manifest SHA`02e1f64ffb8c11d32b7653890c25996a1deb17708b2b6e74f5d9703e09761713`含217项：156份精确副本、60份已存在只读制品及1份S0逐来源处置。处置SHA`16304c09fcd5d11bde706a97265c346271c9a342636a7a6c134c82418e340bcd`绑定83来源/101原决策、全部Example/Action/前缀/lineage/group/split；80来源的98决策排除，3个原始来源恢复。S0另以实际原train/validation核对完整目标覆盖和六类原选择分母；[范围证据](../../reports/S0_P02_QUALITY_V2_SCOPE.md)。复制当前input目录到自己的新scope；其中已存在制品引用只读并逐项核对hash，不能从其他对话的变化中输出自动追加裁定。

允许新增`src/toolalign/data/quality_adjudication.py`、必要的`src/toolalign/data/quality_adjudication_materials.py`、`tests/data/test_quality_adjudication*.py`、`tests/data/adjudication_cases/`原创小fixture、`reports/data/quality-adjudication-r2/`及`coordination/handoffs/P02-quality-adjudication-r2.md`。唯一配置例外：将S0的`P02_QUALITY_ADJUDICATION_CONFIG.v2.json`逐字复制到`configs/data-quality.v2.json`，精确SHA`7cf53c23568cd06c9543f253d9636b4655b135f0e6daf0eb318ace2100807ccb`。其余生产代码、旧测试/配置、协调状态、ADR、依赖及构建配置保持不变；必要共享改动先给S0具体申请。

必须交付新的、可复现的CPU数据视图与verify入口：验证固定manifest、S0配置、原review seals/裁定及处置记录、来源与全部决策关联，拒绝身份/类型/配置替换。依照整来源处置过滤原train/validation；包括有问题目标之前和之后的同来源决策，保留同group其他来源，保持原Example逐行字节、身份、group/split及顺序。3个恢复来源使用原始字节，不能以重标或更改ID代替。UNKNOWN保持未知；排除是训练使用处置，不改写其原语义判定。

输出新版manifest、全部保留/排除/恢复身份及逐Example原因、source/issue/review追溯、有效train/validation与lineage、两profile选择及新的训练数据绑定。选择必须从原始6013/1600及217/197名单过滤，保留原rank和相对顺序，恢复原始例至原rank，不从上一版已过滤集合直接删减，不补选、扩样或按模型分数重排。与旧v1视图的增量单列；旧manifest/数据、32来源原暂挂记录及原失败保持。

| 集合 | 原数量 | FAIL来源排除决策 | UNKNOWN来源排除决策 | 预计有效数量 |
|---|---:|---:|---:|---:|
| train | 7515 | 33 | 61 | 7421 |
| validation | 234 | 1 | 3 | 230 |
| formal train | 6013 | 25 | 48 | 5940 |
| formal validation | 217 | 1 | 3 | 213 |
| smoke train | 1600 | 5 | 12 | 1583 |
| smoke validation | 197 | 0 | 3 | 194 |

以上是S0原身份核对值，须实际生成新输出后验收。正式train比原规划6k下限少60条，按ADR-0024明确记录数量偏差，后续P04按实际5,940条制定配置。新版训练绑定必须绑定新质量政策/manifest/选择、已继承的原表示审计与固定模型profile/格式，training_authorized=false。旧SFT prepare仍硬绑定旧配置，不将本次新数据文件冒称已被真实trainer消费；后续消费适配由S0/T1另派。

本轮不再重标或晋升：原两份直接草案、一份后继、完整token数组及E1/Q1旧意见只作冻结引用，保持staging、不进入有效train或选择；旧观察和超长限制不变。无需再次对这些旧候选分词或试图补出缺失的真实业务结果。

为新有效选择实际生成13例材料：复用`training_review.choose_review_cases`原10例代表规则，来源只在本轮有效train；另用原final/clarify/refuse三个原创协议例，不进训练。选择身份先冻结，再用现有transformers/tokenizers两条CPU路径各处理固定13例，核对完整P/C、IDs、loss/causal mask、唯一EOS、右padding及Example/lineage/原长度审计。复用现有共用formatter、sequence/pad和适用的纯`sequence_record`/`render_page`函数，必要新wrapper只承担新版输入/输出绑定；不复制格式或改旧v1材料模块/常量。输出新结构化材料、HTML及空白AI判定字段，Q1后续独立审核。浏览器实际显示仍NOT_RUN。

验收须有意义：同输入两次新目录构建稳定内容；整来源全部决策隔离、同组其他来源保留、恢复原字节/原rank、无重复/补选/新annotation泄入；hash/配置/来源/Example/处置类型或越界final split输入被替换应拒绝；失败不留下可误认成功的manifest。适用完整CPU回归、Ruff、冻结、公开扫描、diff，以及新sdist/default wheel和从实际sdist重建wheel、一次默认隔离安装的build/verify入口验证。记录实际分母，不将数组元素/安装重复计作独立测试。

仅现有CPU环境，禁用Torch/TF/Flax并离线运行，实际确认未加载模型框架；新增私有制品≤2GiB、新持久环境/依赖/数据/模型下载0。固定13例/engine之外无新分词；全量8228序列不重跑，heldout/test/ood/BFCL不作语义阅读、筛选或训练规则来源，最终集只校验hash/隔离元数据。没有GPU、模型、训练/生成、外部API、浏览器重试、费用或上传。

切换前保存并核验原9b7的440公开文件Git/快照、旧completion与所有原私有制品/链接。新checkout公用路径按已验证6c81解释，以旧Git/快照保存旧seal身份，不声称旧公开路径原字节不变。完整候选、实际命令/退出码/hash、源码时点、失败/NOT_RUN和封存交接后普通推送本新分支并结束。D1不改台账或给自己签PASS，不合并main或放行G-DATA/P04；S0后续安排R1技术、Q1材料/整来源处置核验及main集成。
