# 新格式最终集成｜独立审查通过，CI跟进

2026-09-06，S0。R1 对完整修复 `8c439f683b9d6b04919ff1f7184d8924ccf82f9f` 的正式结论为 **PASS，P0/P1/P2均0**；审查 `b9f7567d7c1066eeb0bff7c47033bb2771eb9594` 已按原SHA公开。原 `7bada2e` 的公开review `2942e568` 仍为FAIL/P2=1；旧反例/数据/审查保持。

S0完整读取五个新审查helper、报告和交接，核验516个路径的源/日志/制品hash，证明 `a5ac6fcdc96dbbc058bad934055d46b9a3fea4ae6ff127ac2072ff5f896b00a8`。对原提交的8个新增可达blob、全部251候选字节与14个既有review分支补核，提交证明 `b5e2482cbf7b7658e2491659d975f5e4d73e9530238ae449ba24d700924991eb`；原未去敏review不是公开祖先。最终completion的505个封存文件及31条原始命令均核对，通过附加证明 `a8e5d7fba7787e42fb9836cad296dca6a7da1832b0e4fb306ef32dd6059efa31`。计数集合重叠，不相加成独立制品数。

R1原反例在源码和实际新默认wheel上两engine均通过；真实reference的声明身份、实际backend和 `!→[0]` 保持，清理后实际API可用。适用675/2加原R1另组60/0为735 passed/2 skipped，reference另13/0含两项HF-only清理；同12例完整普通表示与旧v1相同。旧8,228行仍保持原测量代码/环境/时间，本轮全量重测0。正式[R1交接](https://github.com/kris0516/ToolAlign/blob/b9f7567d7c1066eeb0bff7c47033bb2771eb9594/coordination/handoffs/P02-format-review-r2.md)与原生completed/idle已核验。

S0自己的第一次证据核验脚本误写了既有场景的名称前缀，exit1保留，日志hash `d2d3f09cf0f9b45dc17bbce1cd623cc9ea867c6a0d8d00bc5619d3dd861cd82e`。改为实际 `same_size_tamper_` 并增加精确名称集合后通过，日志hash `df8d84a25f0caee62cce4c9b290237599c1a16c886487c06f37a6afc4508e9db`；R1/候选均未改。它与[S0早期安装环境前置失败](S0_P02_FORMAT_PREFLIGHT_R2.md)分别保留，均不回写为R1本轮失败。

## 实际最终集成与CI

在S0隔离分支从已实际测试的50f7589普通merge原review b9f7567，再普通merge当前main `4a1fa84d2d367ed037a1e39b1d4033f54a385e6a`，得到 `2b11b7fad69957324ecfa671bac71552ec3501b7`，tree `aaabd804ddc3930f944e69a077bfd43c06ad8236`。278个main文件、37个候选新增文件、8个新review文件逐字节保留；47个包文件与839 passed/2 HF-only skipped的组合预检相同。身份核验证明 `764e300ff9e6ee9e042ea5f5546499337e68dcbd7fab7955aa9ffef3f4a78d44`；Ruff/4契约/323路径公开扫描通过。该提交已普通推送PR8，主干未合并。

[CI34024093376](https://github.com/kris0516/ToolAlign/actions/runs/34024093376)对该精确head的首次结果：

| Job | 实际结论 |
|---|---|
| Python3.11 / 101461871696 | 全部步骤成功 |
| Python3.14 / 101461871550 | pytest失败，后续契约/公开/归档步骤跳过 |

3.14.7/Ubuntu24.04.4日志为 **1 failed / 484 passed / 48 skipped，86.61s**。唯一失败位于 `test_monotonic_request_deadline_survives_tool_wall_clock_jump`：结果已timed_out、latency<1500ms、一个model/tool round，但 `tool["operation_started"]` 为false。该测试给予总请求0.6秒，启动进程也消耗此预算，不能保证工具已经开始执行。日志没有证明生产deadline或回收失败；这项启动假设需要修复和独立验证。

GitHub连接器返回的完整decoded job log按UTF-8私有保存，SHA-256 `81931c5cd7ba3fe8c8cfa1aa4dc172220682c28ed2247359422b584092225013`；失败证据 `fc0e5d6f6720318cb35511d64a75e754298ac1d7d402b1176287928e5e14f77b` 绑定实际job/head/checkout及四份未变文件。测试、harness、executor和isolation在当前已验收main与失败候选字节相同；未按绿色的3.11或旧本机结果忽略失败，也未重复运行CI来覆盖它。

E1的[限域CPU跟进](../coordination/tasks/P03_CI_DEADLINE.md)已按完整`fa1ea86361223171a06b5d082a3731b63a00a74a`原生派发，gpt-6-astra/max，新轮ACTIVE已核验；要求受控慢启动/阶段证明、实际阻塞与回收、有效负向控制及精确候选R1复核。PR8保持Draft；格式代码为ACCEPTED，最终集成/main仍未VERIFIED。09:09 UTC共享GPU租约空闲，人审填写副本100行仍0 reviewer/0 verdict，hash保持；G-DATA/P04及完整P00–P09目标未完成。


## E1正式修复交接与R1准备

E1完整候选 `947144fa2dd248113f6db412f120cdae5483c9b8` 已普通推送并读回一致，parent为实测代码 `f69c6a309ff45980c21c2119016f4c5cf8acf8b7`，tree `198606c59676c2fd5e92056d7217dc22c0ee2d8e`。原生本轮completed/idle已核验。仅目标测试、新局部helper与三份交接文档改变；不变生产实现保持原验收范围。

受控0.8秒真实启动复现旧0.6秒测试在operation_started断言失败，请求约704.64ms到期、实际工具停止/回收。新测试按真实启动前/阻塞后阶段推进明确的测试时钟；绕过请求单调约束时，原tool_timeout收尾虽仍得到harness timed_out，共用正向断言实际拒绝。700/1100ms为测试时钟值，不是性能。精确f69完整CPU实际657 passed/0 skipped，含三例及17项真实CPU tokenizer；日志 `1fa81e480d9e787753593260df074b7a5b4457ed6c75ddc5fe48dd67b91f7f01`。

S0完整读取测试/helper、三份交接及验证脚本，核对282候选文件、277原文件不变、15条公开命令与最终19条原始命令、1818件旧文件及2660件新封存条目；集合重叠，实际4767个文件路径。直接解析三份新归档：sdist194485B/89成员，默认和显式重建wheel96713B/47成员；42份生产包载荷与4a1保持，两个新wheel与从精确4a1的45份输入直接构建的基线wheel全部字节相同。证明 `dc09b0aa83cd74e57bae7d8b2641a503b26561f2217398afc750a34011e79c06`；它是交接证据核验，不能替代R1独立结论。

E1保留原失败、负向预期exit1及两次调用设置失败；其辅助inline核对错误只保留交互记录、无独立原stdout/hash，这项限制如实披露。S0首次核对脚本误将旧证据限定在单一私有目录，遗漏三份已记录的历史dist归档，exit1日志 `8d5cbba4370010e214217ac4608494314de867567bea3634f9e5af5fffccef2d` 保留；仅补充三个确切合法路径后通过，日志 `d3452fd5677efc8b7f7858db8298fcf516634e951a56eba8a5ea611d49002988`，候选未变。

[R1精确候选审查范围](../coordination/tasks/P03_CI_DEADLINE_REVIEW.md)已在完整协调提交`c91ea4f79e59e667fd008fab28aaca2e3efdbfe4`准备。10:15 UTC，S0再次以原生状态核验R1原轮completed/idle及干净b9f7567后，按该完整授权实际派发精确947，gpt-6-astra/max，新轮ACTIVE已核验；E1原生completed/idle保持。私有派发回执与新轮身份已保存。10:14 UTC共享GPU租约空闲，100行人审副本仍0 reviewer/0 verdict、hash保持。PR8仍为2b11b7f/Draft；原CI失败未覆盖，新测试独立验收、最终组合CI/main仍待完成，G-DATA/P04保持未放行。
