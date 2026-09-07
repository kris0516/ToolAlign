# S0｜P02 v3 完整候选接收

2026-09-07，**READY_FOR_REVIEW**。D1 完整候选 `5825d789ee89afedbfff31e828223608c6f435e2` 已普通推送、远端一致、原生 completed/idle；S0 于 15:37:36 UTC 完成实物接收。已建立 [Draft PR15](https://github.com/kris0516/ToolAlign/pull/15)。R1 技术、Q1 实际处置／完整材料和最终 CI/main 验证待完成，未关闭 P02-Q-081 或放行 G-DATA/P04。

代码基线 `d3e56f68ebd67cc576d912b6f06636682b4170ab`，原授权 `3e18145b66baa7bce498926869b2d52bd0503453`；实现与实际新编码提交 `6054b349c344cbbad30c12ce8fe8820c59e8bc10`。最终候选仅在该实现上新增报告、证据汇总及交接；561 个已测文件逐字保持，553 个原基线文件不变，全部新增 11 文件均在授权范围。[D1 报告](https://github.com/kris0516/ToolAlign/blob/5825d789ee89afedbfff31e828223608c6f435e2/reports/data/quality-exclusion-v3/README.md)与 [交接单](https://github.com/kris0516/ToolAlign/blob/5825d789ee89afedbfff31e828223608c6f435e2/coordination/handoffs/P02-quality-exclusion-v3.md)保持原文。

## 接收证据

S0 证明 `2eba41c079a18a4e973738c5caf3ca3309bb211a1e5f1f2f80be90620615e379` 绑定 32,579 文件路径、644 链接、564 候选文件、16 授权副本和 347 项原输入。worker completion `1d65726003a5eed3b6b74a4ba77bc0e49cd724d0f0dab82733ac8ec9e3e7cc0f`、收尾回执 `871c318fe264ec84c90a37aeb20b92f07ce71e6992c4ba4b71bd2fea2e04920d` 均已核对。

- 本轮 11,198 私有文件、6,978 测试文件、317 新测试链接和独立收尾文件全数绑定；10 个本轮 pytest 临时目录保留。总新增 733,600,255 bytes，低于 1GiB。
- 原 13,698 路径／327 链接及旧分支、根 identity 保持；492 个旧公共路径通过原 Git 和冻结快照核验，未声称新 checkout 仍为旧字节。
- 44 条记录命令、18 个实际源码 epoch 及最终封存命令核验。44 条完整 metadata 均与原生进程输出一致；40 条命令为直接字面值，4 条检查由明确的顺序循环调用，参数与回执一致。
- 两份实际数据输出各 29 稳定文件逐字一致。已完成的 S0 中间检查再次绑定到最终封存：15,577 原 JSONL 行、7,928 sidecar 的 v1 parent／v2 previous／v3 连续 rank 和旧 11 例完整编码保持。

## 实际数据和编码

| 集合 | train | validation |
|---|---:|---:|
| 有效数据 | 7,419 | 230 |
| formal | 5,938 | 213 |
| smoke | 1,583 | 194 |

84 处置来源／103 局部决策；81 来源／100 决策排除，3 来源／3 决策按原字节恢复。只新增 P02-Q-081 来源的两条整来源隔离；原局部 PASS、旧处置、同 group 其他来源、split 和 staging 边界保持。formal 缺口 62 明列，无补选或重标。

配置 `784aa699026ebb149d720745f461a9cfd493036cd0bf09a72702a81e2db45261`、输入 manifest `ebbaf56bbb5730b5d31eca195d5ac7772d148ff876fc96be1c1c5dbbadf51e06`、输出 manifest `f4569b8b16a6c42bd500cc7c977561b770435954e42ced177e36e857b9776437` 与 quality revision `919ee616fd11993f39bbab6d38146ea827f4bbc3d7bafc07aae0e2c7dd95e5c8` 已逐字绑定。

新编码严格对应 S0 放行 `1eeea3bd45daa8caf5d2867efa5859a446673888993aaaf9cc3a21b80ca555fd`：native 15:02:22–15:02:55 UTC、reference 15:03:52–15:04:26 UTC，均在干净 6054／epoch `6a78def4887e6e41aa3f3e8a02a99f091acbcc42a187d3f30de90027ff707598`。每 engine 两例，总 4/4；旧 11 例重编码 0。预算 reservation、开始／完成事件、原命令与源码均相符。

完整 13 例两 engine 记录逐类型一致，共同 canonical SHA `a41f5c24a55eb5e4fed434b9352b655fbf78e5aa68276de5de183671c81412de`。S0 核对完整 prompt／sequence／padding IDs、attention／loss／causal masks、EOS、所有 padding token_texts 和 Action；22 个复用记录与原静态目录逐字等价，4 个新记录绑定原事件。判定字段均为 null；26 是两路径记录数，独立例数为 13。Q1 的来源 PASS 不替代这次完整材料审核。

## 原自测、归档与限制

D1 默认 CPU **839 passed／48 optional skipped**，新增 73 项包含在 839 中；未重跑无关的 427 项历史报告测试。S0 读取并绑定原日志，没有把这次接收写成独立重跑。实际 sdist 140 成员、两 wheel 各 69 成员；全部载荷、RECORD、metadata 和 64 个安装包文件均与候选相符，默认隔离安装 6 命令退出符合预期。sdist SHA `50881d9f05a35a15825ab55d9b3bd03eb99783f4fc99b56153d706f7446fe642`；两 wheel 同为 `681428cbe1e9638aeab8eb6ed1f123d518021c17279084e7191b6ae52e829f95`。

两次早期原创夹具／断言失败和四次只读查找失败保留；安装中的重复输出退出 1 是原预期拒绝。S0 接收辅助程序另有三次失败：误识别 recorder 源码读取、把 null 判定误期望为空字符串、把含 padding 的 token_texts 长度误期望为未填充长度；原脚本／stderr 保留，修正核验程序后通过，未改候选或旧标签。另一次 `gh` 只读查找因本机无该命令失败，随后使用既有 GitHub connector 创建 PR；没有安装工具。

S0 新数据构建、编码、build/install、框架、模型／GPU和业务 API 均 0。两次完整 v3 构建、4 次新 sequence 的 D1 额度已用尽。R1 后续仅准一次独立完整输出／一次临时安装，真实分词和新归档构建 0；Q1 仅做实际处置与固定材料审核。所有后续人工环节继续由独立 Q1 承接；同问题第五次规则和当前 P02-Q-081 失败计数 1 保持。浏览器实显、真实 trainer 消费及正式模型实验仍 NOT_RUN。
