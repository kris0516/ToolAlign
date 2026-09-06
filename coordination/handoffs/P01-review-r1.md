# P01｜独立审查交接 r1

2026-09-06；owner R1；独立App任务，gpt-6-astra / max；branch `review/p01-r1`。

**结论 FAIL：P0=0、P1=2、P2=1。** 完整被审候选 `59b3802c81aa6eceaf3609af88f288756bcb1581`；生产base `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`；审查授权 `52f9c57a50eaf580a1a90bc5c4b8bd028c83b903`。原候选f97bb0d、P02审查8e4fdbd和所有旧审查分支保留。审查交付的精确SHA由R1原生回报S0，等于本交接单所在提交。

## 范围与契约

已审相对同步授权f2a271b的全部27文件/6,516新增行，包含8个实现模块、41项P01测试、完整历史证据与base-r2同步差异。契约plan-v0.1 / coordination.v1 / toolalign.contracts.v1。155个候选追踪文件逐一核对字节未变，R1仅新增本单和 `reports/review/P01/`。公共契约/配置/锁/状态/ADR及T1工作区均未修改；没有为自己的实现签通过。

## 阻断项与分项验收

| ID | 级别 | 位置与实际影响 | 下一步 |
|---|---|---|---|
| F1 | P1 | execution.py355–378：压力查询异常虽回收自有child，却跳过resources/终态，manifest仍running，汇总漏掉该负结果 | 可靠记录监控失败、child退出码及终态后再结束；不改变回收边界 |
| F2 | P1 | fallback_probe.py182–186：第8步ln2失败发生在原生更新之后，却先于进度/逐步日志记录，漏记完成更新、token和失败loss | 保留实际完成工作与失败事实，再终止；保持2e-6门槛 |
| F3 | P2，非单独阻断 | P01_REPORT.md23：math-r2源码与记录HEAD aaab75e的两份blob不符；全部8份hash实际可绑定47c03404bab043e85b417cd8a6d0432dc2f85479 | 澄清当时工作树来源、登记映射，原raw不改 |

G1(SFT) **FAIL，待F1**；G1(DPO) **FAIL，待F1/F2**。受限SFT与唯一备选的历史功能/数学结果仍得到证据支持，首选mlx-tune仍FAIL；以上不等于本轮新执行了模型实验，更不授权正式P04/P05。

## 验证证据

完整说明、精确位置、最小复现见 [独立报告](../../reports/review/P01/README.md)，命令/退出码/UTC/原始日志SHA见 [机器证据索引](../../reports/review/P01/evidence.json)。

- 217项适用CPU回归通过（58+41+46+72），日志 `3eff019f765a9a5c901fb70ec70f80ae9b785e2e880a310a3357964b153af673`。旧57项结构快照未修改、未冒算通过。
- 独立pytest 4通过/3失败，日志 `915869a915dfe6a791b0aac32a761324c405a850ba43fa4dfe662e62468907fa`；两个F1真实惰性child负例及一个F2原回调CPU隔离负例保留。已确认自有child全部回收、worker失败序列化期间持租约。
- 独立17组float32 CPU loss/解析梯度对照通过，误差均<2e-6，日志 `17307b5921a3e9089effd2d824e287b872ce23ea8e2a0b0fe6522f3cea8cc26e`。T1小Torch CPU脚本在R1环境也实际通过。
- 10个历史run、185项manifest制品、27份原命令日志、两模型实际文件和256条token/mask独立核对；最终日志 `4eef09e75863260bde52eebdc65ca059377b144ac6f73ecd0e7a364f8c7086cc`。逐模型run310个底座array对应原始文件字节、112个adapter array对应保存制品；未构造模型/权重tensor。
- 两锁环境69/90 metadata、64/85 runtime、11源码hash及旧21文件不变得到复核。旧汇总重建SHA仍为 `d0fb9deb067b1e3f6f8b85855a0d1509b3bc15569065bbfed22a5c95928f42bd`。
- 实际sdist/wheel与T1新制品逐字节一致，0未追踪payload；全部8个P01模块和冻结schema验证，默认CPU隔离导入/CLI通过，日志 `fe9038ea66292842050d73dd7368272718b7d01e16768a980d3667514befc3c9`。原共享归档canary、契约冻结、ruff均通过。
- 最终163路径公开内容扫描及8文件新增范围核验通过，日志分别为 `15257e072358989f5ac4fbb3ee53704447d20505e87a8e8cd9ddc5282a424176` 与 `632b3e06c8ef7df766c9a12a0cb2c2b9b96c00fc1613de0281f8124dde6e148e`。

## 保留限制与停止点

首选失败、r2 raw PASS降级、r3具体差值NOT_CAPTURED、1536 pressure2退出124均保留。112SFT=8暖机+104可测/14更新，DPO另8微步/1更新；32-token短生成与容量输入不证明正式数据/256-token完整harness或长时稳定性。reference是sft_smoke，非已验收P04。R1两个检查器自身错误及纠正日志也如实列入报告。

本轮自己的CPU环境/缓存约1.27GiB<2GiB；未GPU/模型重放，未请求新GPU授权。P04/P05、kris token/mask人工核对与P02语义人审、完整P03/正式评测/BFCL、长时稳定性和服务均NOT_RUN；不代kris签名。

S0可按上述最小范围退回T1修订，随后对新精确候选安排独立复核。R1提交并原生回报后结束本轮等待，不自行合并main或启动下一任务包。
