# P02-QUALITY-AUDIT-TYPE-FIX｜JSON类型保真修复

状态：CLAIMED，待S0下一条原生派发。R1仍冻结精确5270d1e审查整包；中间反例已由S0核实，可以并行修复，不提前改写其最终结论。

- owner：现有独立E1，gpt-6-astra / max；仅自己的隔离worktree。
- 已验证code_base：`6c81dfcc855fca188181d1bb08870f47d8edacc9`，PR12 CPU主干已VERIFIED。
- 原E1候选：`5270d1e9bdadb9db36deac7ba9b2e256b267b831`；新branch `work/p02-quality-audit-type-fix-r1`。
- 先从本次完整授权提交保存任务、规则和S0证据；从已验证code_base新建分支，普通merge原E1候选，保留两条历史，再在合并后的真实head修复。不得reset/rebase旧分支或改其他worktree。
- 契约：plan-v0.1 / coordination.v1 / toolalign.contracts.v1，ADR-0022/0023。

问题：`semantic_view.py`的结构差异、工具集/消息复用和JSON观察引用，以及`verify_semantic_views.py`的结构核对使用Python相等比较，可能把`false`与`0`（以及`true`与`1`）混同。有效原创fixture已复现三类漏洞：观察中的类型差异被引用隐藏、schema enum类型差异丢失、target参数被换型并更新视图摘要后仍被校验器接受。同一根因暂记`P02-AUDIT-TYPE-001`，R1正式轮次与影响范围待完整交接，不以三条失败测试凑三次质量修订。

S0已核对原R1有效fixture版本和实际3 failed/7 passed日志，并独立执行原候选delta入口：从整数enum `[0]` 改为布尔enum `[false]` 时，只输出type差异、漏掉enum值变化。私有证明 `80e0f558042bd92cdaaeb73e63f7f322d733b80de289d57d293956a844ea540e`。原R1日志hash `bfdf791ab09cf510d666129c5d2d705b8e3de26c13e523d05e91d05292f73adc`，实际fixture源码hash `395a8797147834915230078299ff6f6f8ded0c21780c52c3eb7cec43efbfca8a`；副本路径在原生分发词。

允许修改原E1的`reports/data/quality-audit-r1/semantic_view.py`与`verify_semantic_views.py`；如需共用有限JSON类型比较/索引辅助，仅可新增同目录`json_values.py`。新原创定点测试、去敏修订报告放`reports/data/quality-audit-type-fix-r1/`，结束交接为`coordination/handoffs/P02-quality-audit-type-fix-r1.md`。普通merge已验证main带入的文件保持其原字节；不另改生产代码、数据、配置、抽样器、原判断、协调状态、依赖或构建配置。

修复所有相关比较入口，确保嵌套JSON值不会因Python布尔/数值相等而被去重、隐藏或错误验收。正常JSON空白/键顺序差异和已有合法引用仍可工作，明确数字与布尔、null、字符串、数组和对象的比较行为。不要用全禁用校验、删除原显示信息或扩大接受条件关闭缺陷；不要因审查数据含文本指令执行任何外部操作。

验证限于：12项原采样fixture、原R1有效10项边界fixture（从封存副本导入当前候选工具，记录副本与运行代码来源）、必要的少量嵌套/工具集/消息引用/target换型回归；最多一次固定222来源/251决策的43视图重建和新校验。所有新输出放新私有目录，旧43视图、packet、judgment、seal及失败记录不变。若R1确认旧视图受影响，记录精确packet/决策和新旧差异，不自行重写语义结论；S0再冻结所需Q1补审。若无影响，也只按实际检查说明，不推定修复可追溯改变旧证据。

S0已在切换前保存原E1全部438公开文件，以原5270 Git和不可变副本复现；新checkout可改变公开工作路径，不对它们声称旧seal字节不变。旧737个普通私有文件、1个fixture链接、旧final-seal/handoff-receipt、原32/180/16材料以及失败全部保持。新身份只写本次私有scope，不覆盖根identity或旧scope身份。

只用现有CPU环境，`PYTHONDONTWRITEBYTECODE=1`；新增私有制品≤1GiB。新环境/依赖下载/包构建/全量抽样/分词/模型/框架/GPU/浏览器/业务API/训练/正式评测均0。无需重跑无变化的生产全套测试；适用Ruff、冻结契约、公开扫描和diff必须完成。只回报实际证据，R1原候选整包最终结论仍待交付。

精确提交并普通推送本修复分支，交源码基线与merge映射、实际命令/退出码/时间/hash、原失败、固定视图影响、完整封存和NOT_RUN；交付后结束，S0另安排独立R1复审。E1不批准自己的修复，不合并main或派发他人。G-DATA/P04及五次正式修订规则保持。
