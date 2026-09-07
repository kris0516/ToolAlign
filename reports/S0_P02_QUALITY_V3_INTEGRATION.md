# S0｜P02 v3 技术接收与隔离集成

2026-09-08，**ACCEPTED（CPU 技术），隔离集成通过**。独立 R1 对完整候选 `5825d789ee89afedbfff31e828223608c6f435e2` 给出 PASS，P0/P1/P2 均为 0；原 review `dbd11d03e69c650efdb330f79ec380dd9914fa89` 已普通推送并核验原生 completed/idle。S0 于 2026-09-07 16:45:58 UTC 接收完整交接，再将原 review 普通合并到隔离分支，实测 839 项 CPU 测试及 21 个拒绝反例、6 个正常对照通过。[PR15](https://github.com/kris0516/ToolAlign/pull/15) 最终 CI、main 验证及 Q1 r5 裁定仍待完成；G-DATA/P04 没有由本次技术验收放行。

范围为 plan-v0.1 / coordination.v1 / toolalign.contracts.v1、Action JSON v1 与 ADR-0025。R1 授权 `7a731c5f08a561f5941fcba5996004706f373392`；D1 实现和四次实际新 sequence 仍绑定 `6054b349c344cbbad30c12ce8fe8820c59e8bc10`。本次没有改动被审实现、原数据或稳定 issue 台账。

## 独立审查接收

S0 核对 **52,757 条实际文件路径、1,235 个链接、30 条 R1 命令及 11 个源码时点**。564 个候选文件不变，review 仅新增七个允许的报告、复核程序及交接文件；全部 571 个公开文件逐字对应 Git，并另存快照。990 个旧公开路径依原 Git/已存副本核对，保留原 R1 `d5b8d17207be7295f3ae5c6a51edd9b8fe968001` 与 D1 v2、旧根身份、原测试目录和历史失败。

R1 原生轮次于 16:41:05 UTC 完成。30 条 recorder 调用、实际退出码及最终 seal 验证均绑定原生结果；其中 29 条完整元数据直接匹配，`independent-data-r2` 的原生显示中间截去 55 tokens，保存的完整 receipt、原 stdout/stderr 和 seal 均存在，实际 session 结束码及可见首尾完全匹配。没有把截断显示写成完整原生全文。

| 封存 | SHA256 |
|---|---|
| R1 completion | `d6d3989372f55c0e03cf734e6459bdc3fb6931e86e5058939cc9e124fa1cc52b` |
| R1 FINAL_FILES | `e3b086b5403909e0dfacab152c331f2f6a899c572b7d00790eeeadb2e5bd0c5c` |
| R1 最终保全 | `924bd1d1abc0187534fcfdc369d4001078b89be507b64ba28b32d9d2c3fc2f40` |
| S0 完整接收证明 | `51870b8dc68081fd8cda189009a5e8fc7046d06850011594b4959c8fe3f75296` |

R1 实测 839 passed / 48 optional skipped；一次独立安装版构建的 29 个稳定文件与 D1 两份原输出相同，15,577 次原行比较、7,928 个三代 rank sidecar 通过；13 个唯一身份、两 engine 的 26 份完整记录和 37,888 行 HTML token 表通过。现存 sdist 140 项、两 wheel 各 69 项及 64 个安装包文件通过。原 D1 44 条命令、18 个源码时点、四次已授权编码及六条安装命令也由 R1 绑定。详见原 [R1 报告](https://github.com/kris0516/ToolAlign/blob/dbd11d03e69c650efdb330f79ec380dd9914fa89/reports/review/P02-quality-exclusion-r1/REVIEW.md)及[交接](https://github.com/kris0516/ToolAlign/blob/dbd11d03e69c650efdb330f79ec380dd9914fa89/coordination/handoffs/P02-quality-exclusion-review-r1.md)。

R1 三次辅助检查失败和两次只读结构显示错误均保留；修正只涉及 R1 的断言及验证层级。最终 boundary helper 仅有 ruff import 排序差异，S0 核对原执行字节及其余 AST 一致。S0 原生命令绑定程序的两次辅助失败亦保留：首次误用 shell 单行解析器读取 heredoc，第二次未处理上述已存在的原生显示截断。修正接收程序后通过，候选及原证据未改；这些不增加正式质量失败轮数。

## 隔离集成与实际验证

隔离分支 `codex/s0-p02-quality-v3` 从 S0 main `4816e4128c3d67ce03dca66e44e4b3471cca4952` 建立。普通 merge `424f1587002dfb4b0c46fa10ecbfbc3997c52c36` 的另一父提交为原 R1 review；原候选及 review SHA 保持。603 个集成文件中，原 main 585 个文件不变，仅新增 D1 11 个及 R1 七个文件；139 个实际 sdist 源成员逐字保持，故复用现有归档和已验安装。

S0 于 16:48:35–16:49:22 UTC 在精确隔离提交实际执行八条命令，均 exit 0，源码前后不变、自有子进程已回收：

| 验证 | 结果 |
|---|---|
| 默认 CPU pytest | 839 passed / 48 optional skipped；独立新 basetemp |
| R1 原创边界 helper | 21 个预期拒绝、6 个正常对照 |
| 所有 tracked Python 文件 ruff | PASS，显式文件列表，无缓存 |
| 契约冻结、公开扫描、diff | PASS；603 个公开路径扫描 |
| 三现存归档对精确集成提交 | PASS；sdist 140、两 wheel 各 69 项，64 个包文件 |
| 已验安装的 v3 verify | PASS；隔离 cwd、64 包文件与集成源码相同，源码目录导入 0 |

CPU 运行记录确认没有加载 tokenizer、Transformers、Torch、MLX 等可选模型模块。旧 427 项无关历史报告组不重跑，48 个依赖真实 tokenizer 的检查如实跳过。安装版 verify 读取冻结输入并核对预期字节，不写第三份全量数据输出。

本次 S0 新归档构建、安装、全量数据构建、真实分词、框架、模型/GPU、训练/生成和 API 均 0。新增私有证据及测试文件在证明创建前合计 95,675,029 bytes；2,614 路径与 149 链接封存，旧临时目录不复用。证明 `8ca7b324d09e1af96d5d609603a053f6c72a79655c1592fb5f508839ef342bb2`，归档检查 `fb3efafa729e079a1ce1beeb747f59595f3601de4a773ac18b19bf3c5e7a9cd8`，安装检查 `df62c80719cd6cb34ead56137e9d727186e199daf9dab9cffff12d890311252b`。完整 argv、UTC、退出码、源码及日志仅在本机封存。

复核入口包括 `pytest -q tests`、`ruff check` 的 tracked Python 列表、`scripts/check_contract_freeze.py`、`scripts/check_public_content.py`、`git diff --check`，以及原 R1 `check_boundaries.py` / `check_archives.py`。完整固定输入路径和隔离 Python 启动参数以本机原命令清单为准；不把示意命令写成另一轮运行。

有效 train/validation 7,419/230，formal 5,938/213，smoke 1,583/194；81 来源/100 决策排除，3 来源/3 原字节恢复。P02-Q-081 是否关闭由 Q1 实际处置裁定后交 S0 登记；当前 82 个稳定问题仍为 81 关闭、1 待修、最高连续失败 1。实际浏览器、真实 trainer 消费和正式模型结果继续 NOT_RUN；旧 `training_authorized=false` 及历史语义失败不改写。
