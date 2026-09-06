# P01-fix-r4 · 启动初始化失败终态

2026-09-06；T1，gpt-6-astra / max。已实现 R2-F1 的定点修复并完成本轮 CPU 自测，**待 S0 安排独立 R1 复审**。原两轮 FAIL 保持原文；不自行改变 G1 验收状态。

| 身份 | 精确提交 |
|---|---|
| 生产 base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| 修复前完整候选 | `ac8095faa58a98e143a8dc4d63042093e426feb0` |
| 原始 R1-r2 FAIL | `aaae5a4395dbdd73fd487f80174599ffd3ef9be3` |
| S0 新授权 | `cbb6d4614c3b8e8f584315ac3bdad434544c3984` |
| 非强制接入原审查 | `65437ea2323f21e6c4c1d7e5b916282209dbd25a` |
| 已测实现及回归 | `2efc7a55ea0dcc77a97cd7f5a82e95515c32de00` |

分支仍为 `work/p01-compatibility`；契约 plan-v0.1 / coordination.v1 / toolalign.contracts.v1。最终完整候选为包含本交接的后续证据提交，精确 SHA 通过 T1 原生回报；已测源码及测试未在后续报告提交中改变。本轮未合并新 main 或无关 P02 变更。

## 复现与修复

先在原审查 merge 上运行未修改的两个初始化反例，**2 failed / 20 deselected，退出1**：初始 swap EIO 时 Popen 调用0次，Popen EAGAIN时调用1次，两者实际创建 child 均0。捕获对象就是原异常；但 manifest 仍 running/ended_at=null/exit_code=null，无 resources，汇总 runs=0。原日志和观察文件保留。

修复将已登记尝试之后的环境准备、swap 基线读取、stdout 打开及 Popen 纳入保护范围；从 `process=None` 开始，只对成功取得的 Process 进行 terminate/有界等待/必要时kill/wait。启动失败与运行期监控错误分别记录，收尾后重新抛出同一个异常对象。正常退出、普通 wait 超时、运行期采样故障、预算/取消和 worker 租约行为沿用原路径，并由未修改的 R1 与完整回归复核。

新增资源字段为 `child_started`、`failure_stage`、`initialization_error`。没有 child 时真实 `raw_process_exit_code=null`；没有读取 RSS 时 `peak_rss_bytes=null`；swap 基线读取失败则 `initial_swap_bytes=null`，已读到的0或非零基线保留原值。没有完整资源样本时，报告中的最大 swap 增长/pressure 都为 null。未启动时不读取不存在的 worker 进度，manifest 保持真实零监督 token/零 optimizer 更新。

报告接口将这些尝试标为 **FAILED_INITIALIZATION**，并显示启动阶段、异常类型、child状态与缺测，不将其混为资源超限。原运行期错误仍是 FAILED_MONITOR。原错误消息仅保存在私有resources；公开摘要只增加必要类型/阶段。

| 原 R1 两例，修复后 | Popen调用 / 实际child | failed / ended_at / exit | swap基线 / RSS / child实际退出 |
|---|---:|---|---|
| initial_swap EIO | 0 / 0 | failed / 已记录 / 1 | null / null / null |
| Popen EAGAIN | 1 / 0 | failed / 已记录 / 1 | 0（探针实际返回） / null / null |

两例汇总各包含一个可识别的 FAILED_INITIALIZATION 尝试，原异常对象传播、原失败证据保持。新增对照另验证基线4096被真实保留；0不等同缺测。已启动child却在首次RSS前发生监控句柄错误时，`child_started=true`、RSS仍null，真实惰性child经SIGTERM回收且退出-15；不将此类运行期错误误称未启动。

## 本轮实际验证

实际 argv、HEAD/源码 hash、起止时间、退出码、完整日志 hash、观察文件及范围清单见 [P01_FIX_R4_VALIDATION.json](P01_FIX_R4_VALIDATION.json)。所有原始日志仅保留私有目录，未覆盖旧命令结果。

- **251项**完整适用CPU及报告检查通过：原238 + 9项新默认CPU回归 + 4项新报告接口检查。
- **29项**未修改R1探针通过：原R1七项 + R1-r2二十二项。
- 本轮合计 **280个不同pytest检查**；开发中的13项、修复前两项和重复运行不再相加。旧shared01的57项结构快照保持原样，未计入通过。
- 新默认回归覆盖environment/initial_swap/stdout_open/Popen四个阶段的smoke和math入口，以及首次RSS前的真实child回收。math入口仍遵循原规则不创建模型run manifest，但保存resources供报告收录。
- 新报告检查调用实际launch后核验FAILED_INITIALIZATION、原异常类别、阶段、child未启动、真实退出缺测、零已执行工作及0/4096基线，不止断言summary长度。
- 全库lint、冻结契约与公开扫描退出0。完整CPU路径禁止MLX/模型/Torch导入；本轮未重复17组独立CPU数学。

主要原始日志 SHA-256：

| 检查 | exit | 日志 SHA-256 |
|---|---:|---|
| before-init | 1 | `f41beaf1db1bae1bb4b7b2d43c5fee540ad115bb3754d542fff89f79649e72fb` |
| full-cpu | 0 | `13411338f82daf738ceefeaaa09e7a0d9c08d7d8d5641d99dcc6718328195398` |
| final-r1 | 0 | `33654704eebe886ac35b8d5e9779daf9f56b55b708f3c249d34bfa70de139efa` |
| build | 0 | `5a5c4fa07cf1ab503200938580bd5a3b4419b89dbd96d955a683e9915546707a` |
| package | 0 | `baebad94cef638c6d304c70d0c4dfa39af8bd235d348a823273f7dcfdf5d41bf` |

## 实际新包与安装后报告接口

`uv build --offline --out-dir <本轮私有build目录>` 的原始日志明确先创建sdist，再从sdist生成wheel。本轮没有执行直接wheel构建，也没有将默认wheel称为直接构建。旧归档不变，新包存独立目录。

| 归档 | 大小 / 完整成员 | SHA-256 |
|---|---|---|
| sdist | 116086 bytes；49文件 = 48追踪 + PKG-INFO | `649b0f757e321294f0a0b193d35c17f3e6785de831e69820e4a413df65241777` |
| 由该sdist生成的wheel | 44830 bytes；27文件 = 22追踪 + 5 metadata | `7c83931ab70668727f824df340ded0ce0530779d9058b8a3c4846aa1f4364ae2` |

[本轮包检查器](P01_FIX_R4_PACKAGE.py) 核对完整成员集合、路径/链接、每项当前Git blob与工作树字节、八个P01模块及冻结schema；未追踪载荷均为0，没有套用旧R1或FIX_R3的包hash。

默认CPU隔离环境离线安装六个runtime distributions，从源码目录之外用 `python -I` 执行 **14条子命令**，全部通过。除原13项安装/依赖/八模块hash与接口/CLI/schema/五fixture检查，新增[安装后启动报告探针](P01_FIX_R4_INSTALLED_PROBE.py)：对已安装的execution分别注入初始swap和Popen错误，实际汇总两个failed尝试并核验异常、缺测和零计数。报告脚本按原分发边界从已核对Git字节的checkout加载，execution来自隔离安装，未伪称报告模块在wheel中。所有14条命令的原始stdout/stderr均独立保存、可重算hash；没有下载新依赖。

## 历史身份与限制

本轮仅修改execution、必要的报告生成器，新增原创回归与R4证据/交接；相对原review九个授权文件变化，相对ac8095f另保留六份R1-r2原始文件。174份未修改的review候选文件逐字节核对，含两轮R1、旧交接和FIX_R3证据。fallback/core/numerical/model_probe/samples、mask/reference/2e-6、公共契约/runtime/配置/依赖/锁及协调文件均不变。

原P01_RESULTS仍为 `d0fb9deb067b1e3f6f8b85855a0d1509b3bc15569065bbfed22a5c95928f42bd`。本轮核对十次历史run已登记的配置/manifest/摘要证据文件身份；185项manifest载荷及17组独立数学结果引用原R1-r2的精确审查证据，没有重复其全量载荷审计或数学执行。F2/F3已独立关闭的结论保持；旧HEAD/工作树映射、首选与备选失败、pressure停止和各轮FAIL不改写。

**NOT_RUN**：本轮MLX/模型/Torch/训练tokenizer导入、GPU/完整math重放、权重或新依赖下载、OS限制调整；17组数学和185项历史载荷的重复执行/全量重哈希；P04/P05正式训练、accepted_sft、kris人工核对、正式偏好生成、完整真后端256-token协议、BFCL/最终测试、长期性能和服务部署。私有CPU环境/制品仍受本轮2GiB预算，实际磁盘快照见验证索引；没有模型资源峰值可宣称。

收尾写入仍依赖可写输出介质；本任务未承诺在磁盘全面不可写时继续落盘。T1提交完整候选并回报后结束本轮，等待S0安排新独立复审；不自行合并或进入训练阶段。
