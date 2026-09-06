# P03-CI-DEADLINE-R1｜截止时间测试独立审查

状态：IN_PROGRESS；S0核验R1原轮completed/idle和干净b9f7567后，于2026-09-06 10:15 UTC按完整授权原生派发，gpt-6-astra/max，新轮ACTIVE已核验。

| 字段 | 本轮值 |
|---|---|
| owner | R1，既有独立Codex任务及隔离worktree |
| 精确被审候选 / code_base | `947144fa2dd248113f6db412f120cdae5483c9b8` |
| E1测试代码提交 | `f69c6a309ff45980c21c2119016f4c5cf8acf8b7`，父为已验收main `4a1fa84d2d367ed037a1e39b1d4033f54a385e6a` |
| E1授权 | `fa1ea86361223171a06b5d082a3731b63a00a74a`，见[P03-CI-DEADLINE](P03_CI_DEADLINE.md) |
| authorization_commit | `c91ea4f79e59e667fd008fab28aaca2e3efdbfe4`；切换前以git show读取并私有保存 |
| 新审查分支 | `review/p03-ci-deadline-r1`；保留旧review/p02-format-r2和全部既有refs |
| 模型 / 推理 | `gpt-6-astra` / `max` |
| 契约 / 协作 | toolalign.contracts.v1 / coordination.v1 / plan-v0.1 |
| 审查交接 | `coordination/handoffs/P03-ci-deadline-review-r1.md` |

## 范围与证据入口

本轮只审查旧P03截止时间测试的修订及其证据。新格式8c439f6已由R1以原review b9f7567正式PASS；PR8最终组合2b11b7f在[CI34024093376](https://github.com/kris0516/ToolAlign/actions/runs/34024093376)的Python3.14失败。源测试与执行器在4a1和失败组合中相同，原始CI失败及S0核验见[跟进证据](../../reports/S0_P02_FORMAT_CI_FOLLOWUP.md)。不merge新格式或后续main，不把本轮结果代替最终组合CI/main验证。

被审入口：`coordination/handoffs/P03-ci-deadline-r1.md`、`reports/harness/P03_CI_DEADLINE_VERIFICATION.md`、`reports/harness/P03_CI_DEADLINE_EVIDENCE.json`，以及与4a1的完整diff。E1完整候选身份与S0证据核验：S0核验282份候选字节、277份原文件保持、15条公开命令与最终19条原始命令、1818份旧私有文件及2660份新封存条目；集合重叠，实际核对4767个文件路径。证明SHA-256 `dc09b0aa83cd74e57bae7d8b2641a503b26561f2217398afc750a34011e79c06`。E1原生completed/idle已核验。

仅允许新增 `reports/review/P03-ci-deadline-r1/` 下审查报告、证据索引和必要小型独立探针，以及本轮交接单。候选所有文件、src、测试、旧reports/review、依赖/配置/CI、协调状态、其他worktree和所有旧私有证据均只读。不得修改被审实现后签PASS；不能使用未去敏旧review提交作为公开祖先。原生任务ID、本机绝对路径和原始日志中的私有内容只存本机。

## 要回答的验收问题

1. 精确候选是否仅包含获准的目标测试、局部helper和本轮三份交接/证据文件；已验收生产包和旧测试/审查是否逐字节保持。代码f69与最终候选之间如有变化，按最终实际diff重新核对，不能假定是文档变化。
2. 原0.6秒测试的失败是否由实际受控慢启动复现；原test_harness、当时未追踪helper、私有launcher和原命令/log是否绑定实际来源。独立验证关键因果：工具尚未进入执行仍可正确到期并回收，不能用这条路径代替“真实工具已开始阻塞”的验证。
3. 两个阶段的真实子进程、原生产block分支、无结果、实际停止/exitcode/join回收、目录清理是否有证据。检查时钟/UTC remainder替身的作用边界及真实watchdog，不能将测试时钟latency当作实际性能数字，不能伪造进程或清理记录。确认测试不再依赖0.6秒内完成spawn。
4. 移除请求单调约束时，共用正向断言是否确实拒绝仅靠tool_timeout收尾的运行。负向控制的真实结束与自有进程清理必须有界；原始预期exit1要保留。只看最终harness也timed_out不足以证明请求截止生效。不能把捕获预期失败的单个pytest PASS再当作额外独立成功场景。
5. 在精确最终候选实际执行相关正负控制和适用的完整CPU回归，覆盖未改harness/工具生命周期；保留全部失败、跳过和执行环境。完整组已含目标三例时不重复相加。对初次缺psutil和随后basetemp命名空间错误，核对原日志/调用设置与修正后的实际结果，不能回写为PASS或改旧测试绕过。
6. 核对实际新sdist、默认wheel与显式从sdist重建wheel的完整成员、Git载荷及隐私边界。确切4a1基线包输入与新候选生产wheel必须一致；历史不同README的wheel不是本轮基线。候选默认/显式重建路线与额外基线源码wheel路线分别记录。源/包字节未变时不重复扩展未改安装、模型或全量数据审计。

Ruff、冻结契约与公开内容扫描必须通过；必要的独立探针应围绕上述实际边界，不建立通用时钟/进程框架，不重开已验收P01/P03或已PASS格式的整包实现。

## 资源与交接

仅CPU，复用既有纯CPU环境和已核验tokenizer来源，原路径由S0私有派发；不安装新环境、下载模型、导入模型框架、占GPU、训练/正式评测/BFCL、填写人审或产生费用。新增私有制品上限2GiB。D1/T1/E1没有并行实现授权；R1是独立审查，不占实现名额。

输出明确PASS/FAIL/BLOCKED与P0/P1/P2，列精确被审candidate、review commit、parent/tree、命令和原始日志hash、来源/制品身份、实际进程清理、失败与NOT_RUN。形成完整交接、提交本轮允许的新文件后结束并回报S0，等待S0验收和普通集成；不合main、不推旧分支、不自行重跑或合并PR8。R1 PASS不自动完成最终组合CI/main、G-DATA或P04门槛。
