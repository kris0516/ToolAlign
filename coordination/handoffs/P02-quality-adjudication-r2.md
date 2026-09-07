# P02-QUALITY-ADJUDICATION-r2 — D1 交接

状态：READY_FOR_REVIEW，等待独立 R1/Q1 与 S0 集成。工作分支 `codex/p02-quality-adjudication-r2`；code_base `6c81dfcc855fca188181d1bb08870f47d8edacc9`；授权 `f8b81b9783892669d19aafee5a1d82a4a8409cd3`；model=gpt-6-astra / thinking=max。契约 plan-v0.1 / coordination.v1 / toolalign.contracts.v1。

生产与测试提交 `f7acd93595bfeb5e81b6eafe53c8d4106ce10a68`；原编码源码字节提交 `d64531c6ae648b6f314c9b2a5b10b321f5adedf9`。本文件和证据摘要随最终交付提交提供，精确完整候选 SHA 与私有封存 hash 由同次原生消息交给 S0。

范围为两个新增 data 模块、逐字 S0 v2 配置、53 项原创 CPU 测试及本轮报告/验证脚本。无旧生产、契约、依赖、构建配置、协调状态或 ADR 修改。

实际交付：217 项固定输入；83 来源/101 决策；整来源排除 80/98；原字节恢复 3/3。有效 train/validation 7,421/230；formal 5,940/213；smoke 1,583/194。受影响 group 内其他来源为 5,182、决策为 5,553。选择沿用原 rank、不补齐，formal 的 60 条偏差如实登记。新 manifest SHA `0b0fdb79f728256dac42ddba75e0f3fc43aebb9502f2e9097398a482d5774251`；两次修正后实际构建 29 稳定文件一致。

固定 10+3 例在两引擎各实际编码一次；后续仅静态复用原 26 份完整记录及两组各 28 份 payload。完整记录 SHA `330ce458bb7983d911a1adbfee797bdf82e6f93c7c3cb4e1144f5e767c036f06`；原编码时点与原生产源码单独保留，未重新分词。AI 判定字段为空，旧三份 staging 保持冻结引用。

验证：1,193 passed / 48 tokenizer-related skipped，53 新增已包含；110 subtests 单列。默认 tests 在最终修正源码下 766/48，旧不受影响分组 427/0。S0已确认不补跑额外分词 fixture，不能冒称旧 1,186 环境重跑。实际三归档、默认隔离安装6命令、Ruff、冻结、公开扫描、diff通过。完整报告与命令 hash：[README](../../reports/data/quality-adjudication-r2/README.md)、[evidence.v2.json](../../reports/data/quality-adjudication-r2/evidence.v2.json)。

保留失败：intake 枚举假设、seal 轮次同名绑定、材料顶层 revision 负例、两轮 Ruff 原日志；S0 中间发现的来源/决策分母误标与旧349e manifest保留。以上已在候选修正，正式失败增量由S0按政策维护。旧9b7候选、440旧公开文件Git/快照、旧私有制品/链接与原意见保持；最终保全检查使用旧Git/快照解释已切换的公开路径。

另保留最终检查前私有 wrapper 快照并行创建竞争：三个请求的检查当时未执行，逐条重启后 Ruff、冻结和 diff 均通过；原启动事件与实际检查结果分开封存。

NOT_RUN：浏览器实显、训练消费、模型/GPU、业务工具重执行、全量分词及正式评测。新增下载/持久环境0；最终新增私有制品预算由completion精确登记。R1技术、Q1逐来源/材料判定、S0 main、G-DATA与P04未验收。D1不合并main、不自签独立PASS、不修改台账或引入PR13后的实时输入。
