# P02-QUALITY-REMEDIATION｜委托AI审查后的数据整改

状态：ACCEPTED（CPU技术范围），PR12最终集成/CI/main待完成。完整9b7cf019b1d55501a7e656dbfb79b13bc7369fa0与原R1 PASS1e45cf2已由S0接收，14,011路径证明bda9b18f；见[S0接收报告](../../reports/S0_P02_QUALITY_REVIEW_ACCEPTANCE.md)。以下保留原派发与范围，本包不放行G-DATA或正式训练。

- owner：D1；只用现有独立Codex任务及其隔离worktree，gpt-6-astra / max，禁止sub-agent。
- code_base：`86b80bada50ac7c8f4b3910e3831a397ed65a853`。
- branch：`work/p02-quality-remediation`。从上述已验证main新建；保留原`work/p02-training-binding`及所有旧制品，不reset/rebase/覆盖旧分支。
- authorization_commit：由S0下一条原生分发消息给出完整SHA；先读取该提交的本任务、ADR-0022和配置并保存私有副本，再切换基线。
- 契约：plan-v0.1 / coordination.v1 / toolalign.contracts.v1。冻结契约、旧v1数据/选择/序列、旧报告和失败证据保持。

## 输入与所有权

输入为已验证原数据、原训练选择和P02-DELEGATED-AI-REVIEW-r1封存材料。具体本机路径由私有分发词给出，公开配置仅绑定hash。S0已核对21份封存文件、63份冻结输入、两份CSV身份与AI审阅者；此为交接核验，不是新数据或G-DATA验收。原报告标记20个fail来源和12个unknown来源，全属train；标签属于审查者判断，暂挂不要求先假定外部API已实际证实错误。

允许新增`src/toolalign/data/quality_revision.py`、必要的`src/toolalign/data/quality_materials.py`、`tests/data/test_quality_revision.py`、必要的`tests/data/test_quality_materials.py`及`tests/data/quality_cases/`原创小fixture、`reports/data/quality-remediation-r1/`和`coordination/handoffs/P02-quality-remediation-r1.md`。唯一配置例外：把S0的`P02_QUALITY_REMEDIATION_CONFIG.v1.json`逐字复制到`configs/data-quality.v1.json`。其余生产代码、旧tests、公共状态/ADR/依赖/构建配置均只读；需要共享改动先向S0提交具体申请。

## 本轮必须实际交付

1. 实现可复现的CPU质量修订视图。读取精确原manifest和已封存审查，验证CSV/提案/source/Example/group/split关联后，暂挂全部32个来源的全部原规范化决策（包含错误决策之前的同来源决策及之后的历史前缀）。原文件不改，其他来源原Example字节、身份、group和split不变，不删整group、不重新分组切分。
2. 输出新的train/validation视图、逐Example暂挂原因、来源与旧身份追溯、保留/排除清单及新版本manifest。原train7515条中报告标记fail来源26条、unknown来源14条，暂挂后7475；validation234条不受这份提案影响。这是S0核对值，仍须本轮实际生成及核验。
3. 重建本修订视图的训练选择和配置绑定：从**原已选集合**逐条去掉暂挂来源，保留相对排名和旧rank追溯，不用其他未审样本补足smoke数量。当前提案核对值为formal/train6013→5980（22+11条暂挂）、smoke/train1600→1593（3+4条），validation仍217/197。新manifest明确原分母、继承的原序列依据、新质量修订hash、有效集合及training_authorized=false，不能改旧v1常量或伪造重新分词时间来接受新输入。
4. 对两份重标草案制作**独立候选**：只应用已列出的精确Action变更，验证原Action hash、原schema和用户原始依据，按新期望Action重建Example规范化hash/ID、annotation-parent与理由。保留原source_record_hash及原group/split，修订来源放在新的annotation sidecar，不伪造上游revision。候选先留在quarantine/staging，**不进入本轮有效train或选择**。前序调用变动后的旧合成观察不能冒充重新执行结果；重建受影响后续前缀的可审查候选并标未验证，无法证明的后继继续隔离。尤其聚类候选不能因补参数就宣称原观察已重新验证。
5. 两个重标候选实际重新生成当前格式的P/C、完整IDs/mask/shift/EOS/padding及来源绑定；从本轮有效选择中按原材料规则选择10个真实train代表例，另保留3类原创协议例。原10例中的被暂挂项不可继续充当有效训练例。用两种已有CPU tokenizer路径核对新材料，输出可供委托AI复核的结构化材料；不填kris或AI的语义结论。与E1协调的新审阅结果须经S0精确授权后接入，不能从变化中的共享文件自动追加标签。

## 验收与资源

新增私有环境/依赖下载0，复用现有CPU环境；禁用Torch/TF/Flax并离线运行，实际核对未加载模型模块。新制品上限2GiB；无模型、GPU、训练、生成、外部API、浏览器重试或费用。原数据和任意测试集只允许完整hash/隔离元数据核对，不能把test/ood_test/BFCL语义或答案用来制定规则。不要重跑无差异的全量tokenization。

PLANNED：提供`python -m toolalign.data.quality_revision build/verify`（具体参数随实现交接）、质量修订的正负例、适用完整CPU回归、Ruff/冻结/公开扫描，以及新的sdist/default wheel及一次从实际sdist重建wheel和默认安装入口验证。原纯默认环境不引入tokenizer依赖；实际新token材料另在已有允许环境核验。

有意义的边界：同输入两次新目录生成稳定内容；来源/Example/CSV身份、输入hash或配置被替换即拒绝；final split及越界身份拒绝；同来源后继完整隔离而同group其他来源保留；无重复/回填/重排；旧材料与旧错误保持；变更Action确实更新ID并保留parent，后继未知观察不获得通过；候选不泄入有效训练；任何错误不得留下可误认成功的manifest。报告实际用例和分母，不把数组元素或安装重复计作独立测试数。

交完整candidate SHA、原始命令/退出码/hash、生成制品与输入绑定、失败/NOT_RUN和上述handoff后结束本轮。不得自行合并main或将本包标G-DATA/P04通过。R1后续独立审查，E1扩展审计仍是单独依赖；本轮完成不等于32个来源都已修成可训练正例，更不认证未审语义。
