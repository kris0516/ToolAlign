# P02 quality adjudication v2 — D1 交付证据

状态：READY_FOR_INDEPENDENT_REVIEW。这里只登记 worker 实测；R1 技术审查、Q1 处置/材料审核、S0 main 验证及 G-DATA/P04 仍待完成。

基线 `6c81dfcc855fca188181d1bb08870f47d8edacc9`；S0 授权 `f8b81b9783892669d19aafee5a1d82a4a8409cd3`；生产与测试 `f7acd93595bfeb5e81b6eafe53c8d4106ce10a68`。契约保持 plan-v0.1 / coordination.v1 / toolalign.contracts.v1。唯一配置新增为逐字采用的 `configs/data-quality.v2.json`，SHA `7cf53c23568cd06c9543f253d9636b4655b135f0e6daf0eb318ace2100807ccb`。旧 v1 代码、配置、制品、意见和分支保持。

## 数据处置与实际分母

固定 217 项输入绑定 83 来源/101 决策，采用独立 Codex AI 的既有裁定。80 来源的全部 98 个决策排除；3 来源/3 决策恢复原始字节。当前 Action 的判定与整条来源的训练适用性分开记录；UNKNOWN 保留未知，整来源排除也覆盖局部 PASS 和前后继决策。

| 集合 | 原选择 | FAIL 来源排除 | UNKNOWN 来源排除 | 实际有效 |
|---|---:|---:|---:|---:|
| train | 7515 | 33 | 61 | 7421 |
| validation | 234 | 1 | 3 | 230 |
| formal train | 6013 | 25 | 48 | 5940 |
| formal validation | 217 | 1 | 3 | 213 |
| smoke train | 1600 | 5 | 12 | 1583 |
| smoke validation | 197 | 0 | 3 | 194 |

保留的 7,651 条 train/validation Example 均使用原 JSONL 行字节，身份、group/split、顺序及原 lineage 不变。受影响 group 内仍保留 **5,182 条不同来源、5,553 条决策**。原中间 manifest 的 `other_sources_retained_in_affected_groups=5553` 曾误标分母，已由 S0 指出并修正；旧 manifest 和原两次构建仍保留。

两 profile 均从原名单过滤，保留原 rank，不补选、不重新拆分。三个恢复例中，只有一个原本属于 formal/smoke train，按原 rank 返回；其余两个不会因此获得新选择资格。formal train 比原 6,000 下限少 60 条，按 ADR-0024 将真实 5,940 条登记到后续配置准备。

修正后两个新目录实际构建的 29 个稳定文件逐字节一致；manifest SHA `0b0fdb79f728256dac42ddba75e0f3fc43aebb9502f2e9097398a482d5774251`，内容 revision `615248b9a9ed05a6753fab546c547579c24c0d23adc36528ad4d85784919f8ff`。28 份数据 payload 与修正前完全相同。独立于 producer 的 worker stdlib 交叉核对见 [check_revision.py](check_revision.py)；完整结果摘要与实际文件 hash 见 [evidence.v2.json](evidence.v2.json)。

新版输出包含全部保留/排除/恢复身份、逐 Example 处置原因、来源/issue/review 追溯、有效数据与 lineage、原 rank 选择、v1 增量以及新的训练绑定。原三份 staging 仅作冻结引用，不晋升、不重新分词。训练绑定的 `training_authorized=false`；旧 SFT prepare 的输入绑定没有改变，真实 trainer 消费仍为 NOT_RUN。

## 固定材料与真实编码时点

先冻结原规则选出的 10 个有效 train 代表例，以及原 final/clarify/refuse 三个协议例。随后现有 tokenizers 与 transformers CPU 环境各实际编码同一批 13 例，完整 P/C、IDs、loss/causal mask、唯一 EOS、右 padding、Example/lineage 及原审计均核对。两路径完整记录 SHA `330ce458bb7983d911a1adbfee797bdf82e6f93c7c3cb4e1144f5e767c036f06`；26 是两条路径的实际测量数，独立例数为 13。协议例不进入训练，AI 判定字段保持空白，浏览器实显 NOT_RUN。

原编码发生在本轮原日志所记 2026-09-07 11:09–11:11 UTC；当时源码字节后来完整保存于 `d64531c6ae648b6f314c9b2a5b10b321f5adedf9`，不把该提交时间或后续源码冒称为原执行时点。计数与 verifier 修正后，[republish_materials.py](republish_materials.py) 从固定 manifest hash、Git 源码字节和原 run 重新核对证据，在新目录静态封装；两路径各 28 份 JSON/HTML/CSV payload 完全复用，**新增编码 0**。新 manifest 同时保留 `original_encoding` 与 `static_republication`，原材料不覆盖。

## CPU、拒绝行为与归档

实际 1,193 项 CPU 检查通过，48 项额外 tokenizer 相关检查按 S0 确认的 13 例/engine 边界跳过；110 subtests 单列。其中默认 tests 修正后为 766/48，旧边界报告分组为 427/0，53 项新增测试包含在总数内。没有把重复运行、数组元素或安装命令计作独立 pytest。此环境与旧 1,186 项验收环境不同。

新增反例覆盖整来源的全部决策、同组其他来源、原字节/rank 恢复、缺失/重复/替换身份、final split 越界、bool/int/float 替换、原 review seal、元数据替换、输出替换和失败不发布 manifest。D1 额外反例曾复现材料顶层 revision 重新声明可被接受；已补齐 revision 和固定 parent tokenizer 身份检查。首次 intake 枚举假设、seal 同名歧义、该反例及两轮 Ruff 失败原日志全部保留，修正后检查通过；不在 D1 修改正式失败台账。

最终检查启动时，私有日志 wrapper 的新源码快照出现并行创建竞争，三个检查尚未执行即退出；该事件单独保留，改为逐条执行后的 Ruff、契约冻结及 diff 均通过，不将启动失败记作这三项检查的实际执行结果。

实际 sdist 含 134 个成员；默认 wheel 与从该实际 sdist 再构建的 wheel 各含 67 个成员且字节一致。成员、RECORD、元数据和 62 个包文件已绑定当前提交。默认隔离安装使用现有纯 CPU 依赖目标、`-B -I -S`，6 条命令实际验证安装、API/空依赖守卫、help、新目录 build/verify 及原输出 verify；源码 cwd 导入 0、额外模型/分词包导入 0。见 [check_package.py](check_package.py)。Ruff、契约冻结、公开内容扫描和 diff 检查通过，最终封存另绑定原始日志、源码 epoch、归档和旧制品保全映射。

复现数据入口接受精确配置、固定输入目录和新私有输出目录：`python -m toolalign.data.quality_adjudication build|verify --config-path … --input-root … --output …`。材料入口为 `quality_adjudication_materials freeze|measure|compare`；本轮测量额度已经使用完毕，最终核验静态使用原 13 例数组。

新增持久环境、依赖/数据/模型下载、GPU、模型训练/生成、全量 8,228 序列重跑、业务工具重执行和公开模型/数据上传均为 0。heldout/test/ood/BFCL 未用于语义阅读或训练规则；最终集仅 hash/隔离元数据校验。最终候选 SHA、私有路径与封存 hash 由原生交接提供给 S0。
