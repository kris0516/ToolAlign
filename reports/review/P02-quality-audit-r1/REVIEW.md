# P02-QUALITY-AUDIT-REVIEW r1

**FAIL — P0=0，P1=0，P2=1。** R1 对完整候选 `5270d1e9bdadb9db36deac7ba9b2e256b267b831` 的 CPU 技术审查发现 JSON 类型保真缺陷。固定抽样、已有判断导出和本批冻结材料的实值核对通过；不能据此把有缺陷的展示/核验脚本签为 PASS。

| 审查身份 | 精确范围 |
|---|---|
| reviewer | 独立 Codex-AI(R1)，gpt-6-astra / max |
| 授权 | `769f9ffc7faf0025900da0035d6309fc975e338f` |
| 实现基线 | `86b80bada50ac7c8f4b3910e3831a397ed65a853` |
| 采样器 / 内容提交 | `7298456d5b54361beed0df681964078bc200957a` / `e5030e917e249eaa456f116b1b6490abae9c7e30` |
| 审查分支 | `review/p02-quality-audit-r1` |
| 契约 | plan-v0.1 / coordination.v1 / toolalign.contracts.v1 |
| 完整变更 | 438 个候选文件、428 个不变基线文件；全部 10 个新增文件，包括六个 Python 脚本、三份报告与 E1 交接 |

R1 只新增本审查目录和[交接单](../../../coordination/handoffs/P02-quality-audit-review-r1.md)。原实现、数据、判断及协调台账未改；后续 E1 修复候选不属于本轮。

## F1 / P02-AUDIT-TYPE-001 — P2，JSON 比较混淆布尔值与数字

[`semantic_view.py`](../../data/quality-audit-r1/semantic_view.py) 的第 25、118 行用 Python `==` 判断结构或观察值是否相同；第 93、108 行的工具集/消息去重使用同类比较。[`verify_semantic_views.py`](../../data/quality-audit-r1/verify_semantic_views.py) 的第 103、114、116 行，以及 [`check_materials.py`](../../data/quality-audit-r1/check_materials.py) 的第 193–194 行，也据此声明显示内容一致。Python 将 `False` 与 `0` 视作相等，JSON 的 `false` 和 `0` 则具有不同类型。

有效原创夹具和一份新私有材料副本复现了四种表现，全部归入同一问题：

1. 原观察为 `{"ok":0}`、规范化前缀为 `{"ok":false}` 时，renderer 将后者改为指向前者的 `equal_json_value_ref`。布尔值从显示中消失，反向核验仍通过。
2. schema 的 `integer`/`enum:[0]` 改成 `boolean`/`enum:[false]` 时，delta 只记录 `type` 变化，遗漏 `enum` 变化。
3. 仅将显示 TARGET 中的布尔参数 `false` 改为 `0` 并重算该视图摘要，反向核验不拒绝；未修改冻结 packet。
4. 仅在新 HTML 副本的完整 Example 区块中，将 `additionalProperties:false` 改为 `0`，保留原记录、prompt 和 token 表，`inspect_record` 仍返回 `static_html_content_exact=true`。原页和原记录未改。

这会隐藏或接受审计对象与展示内容之间的类型差异，直接削弱逐条语义阅读和材料一致性检查。修复应在 JSON 值比较、去重、delta 及反向核验中使用一致的类型感知规则，并覆盖材料 JSON 区块；不能仅修正某一个失败例或关闭断言。修复和独立复审由 S0 组织。

公开[原创边界测试](test_independent_boundaries.py)在精确候选上为 **3 failed / 7 passed**。材料反例另有一次预期不通过的断言。复现、源码快照及原始输出摘要见 [EVIDENCE.json](EVIDENCE.json)；私有材料反例不公开。

## 本批材料的实际影响

R1 使用独立的 JSON 类型比较重建已有 43 份视图，核对 **222 个来源、251 个目标、628 个原始 turn、660 条累计前缀消息**，类型差异为 **0**。16 份现存材料的 **64 个 JSON 区块**也未发现类型差异。这是对冻结材料内容的机械核对，不是重做来源语义裁定，也不关闭脚本缺陷。

一次真实取样重放复现了原固定名单：有效池 7,113 个来源，先取 96 train / 24 validation，再按固定顺序取六批各 10 个定向来源，无重叠、补选或 heldout 导出。独立核对了排名、触发规则、110 个原审来源排除、全部有效 Example、group/split、原文/目标/前缀绑定及先冻结后判断。原 32 来源单列，新增 180 来源共 200 个决策。12 项原始取样 fixture 通过；新增边界测试同时确认未调用工具和无效决策不会误触发，重复物理来源仍保留全部有效目标，错配来源/目标与漏目标会被拒绝。

一次已有判断汇总复现了 222/251 导出。七份 CSV/JSON 导出逐字节相同，summary 仅生成时间不同；CSV 的 10,184 个字段及问题来源、override、分母分别核对。87 个 Action 问题为 24 fail / 63 unknown；1 个历史 advisory 单列，79 个来源处理建议仍为未实施建议。追加材料的 10 个额外来源 / 11 个目标与原文件绑定通过；三个 staged 材料复用两个原审来源，未并入新增来源分母。

16 份既有 token/mask 材料的完整数组和 26,112 行 HTML token 表通过静态核对；没有运行 tokenizer 或浏览器。上述计数忠实反映既有 E1 判断，不作为全库错误率、全库语义正确或训练授权。

## 证据、失败保留与限制

Intake 核验了 E1 的 737 个普通私有文件和 1 个不跟随的链接、S0 原证明中的 4,536 路径，合并去重核验 8,644 路径。原 R1 的 3,216 个私有文件、186 个链接及 450 个公开文件的原 Git/不可变快照保存关系保持。原公开文件按旧 Git 和快照验证，不把新 checkout 路径误称为旧原件。

E1 26 条原命令的记录、输出 hash、UTC、exit、HEAD/index tree 与执行源码映射核对通过。其 logger 在子进程完成后读取 HEAD，提交命令记录的是结果提交；早期未追踪脚本通过原 worktree manifest 绑定，未冒称在最终 HEAD 执行。原材料检查器误用旧 HTML 区块、原封存脚本拒绝 fixture 链接的两次 exit1，以及各自失败源码/修正均保留。

R1 的四次辅助夹具/核验脚本错误也保留：误将后续 packet seal 当作 sampler 输出、夹具使用不支持的 schema 字段/缺少字符串上限、CSV 可选字段读取假设、选中无工具协议例。修订后的检查分别完成；这些不是候选新增问题。有效反例的失败不被这些辅助错误替代。额度中断仅中断执行，不构成审核结论或修订失败。

本轮仅使用现有 Python 3.14 CPU 环境；真实抽样、已有判断汇总、43 视图重建各一次。未重评 180 个来源，未读取 Q1 的新语义裁定，未重复生产全套回归，无新环境、依赖、构建、模型/框架/GPU、业务 API、训练或正式评测。G-DATA/P04 未放行。

`F1` 与 S0 的稳定问题 ID `P02-AUDIT-TYPE-001` 是同一根因。本轮正式事件建议为一次 FAIL，P2=1；四种表现、重复检查、辅助夹具失败及额度中断均不增加正式修订次数。R1 不修改正式问题台账。完整 review SHA、最终发布检查和封存摘要随原生交接登记。
