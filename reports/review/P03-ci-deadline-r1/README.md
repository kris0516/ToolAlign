# P03-CI-DEADLINE-R1 独立审查

2026-09-06，R1，gpt-6-astra / max。**PASS；P0=0、P1=0、P2=0。** 结论限于精确候选的截止时间测试修订及证据。原测试对 spawn 速度的假设已被实际反例定位，新控制能够区分请求取消与稍后的工具超时。生产包逐字节保持。

| 身份 | 精确值 |
|---|---|
| authorization | `c91ea4f79e59e667fd008fab28aaca2e3efdbfe4` |
| candidate / parent | `947144fa2dd248113f6db412f120cdae5483c9b8` / `f69c6a309ff45980c21c2119016f4c5cf8acf8b7` |
| candidate tree | `198606c59676c2fd5e92056d7217dc22c0ee2d8e` |
| 输入基线 | `4a1fa84d2d367ed037a1e39b1d4033f54a385e6a` |
| 审查分支 / parent | `review/p03-ci-deadline-r1` / 上述 candidate |
| 契约 | plan-v0.1 / coordination.v1 / toolalign.contracts.v1；冻结保持 |

审查 commit/tree 在提交后按实际 Git 对象回报 S0，并封存在私有 completion；包含本报告的审查提交可由 `git log -1 --format='%H %P %T' -- reports/review/P03-ci-deadline-r1/README.md` 读回。[机器证据](evidence.json)登记具体命令、原日志 hash、完整归档成员与限制；[交接单](../../../coordination/handoffs/P03-ci-deadline-review-r1.md)供 S0 集成。

## 范围与来源

完整 diff 只有目标 `test_harness.py`、新 `deadline_cases.py` 和 E1 三份交接/证据文件。f69 至947的实际 diff 仅三份文档。282份候选文件在R1与E1工作树均匹配Git，277份其他基线文件保持；42份生产源码/资源、其他测试、旧审查、依赖、配置、CI和协调状态未改。本轮仅新增本审查目录及交接单，15条既有 review refs 保持，旧未去敏提交不在候选祖先中。

R1重新逐项计算 S0 已封存清单中的4767个实际路径 hash/bytes，并核对19条 E1原命令/log、15条公开命令的参数展开及元数据。1818条旧私有证据与2660条新封存条目存在交集，不能相加。五份既有tokenizer来源保持，未写其他工作树。S0 proof SHA为 `dc09b0aa83cd74e57bae7d8b2641a503b26561f2217398afc750a34011e79c06`；其角色是输入证明，本报告结论来自本轮独立检查。

原CI日志在Python3.14.7/Ubuntu24.04.4为1 failed/484 passed/48 skipped，失败位于原709行。R1验证四份相关文件在精确4a1与失败组合2b11中相同，原decoded log SHA为 `81931c5cd7ba3fe8c8cfa1aa4dc172220682c28ed2247359422b584092225013`。该历史失败没有被改写为本候选结果。

## 原失败与三个控制

R1私有重放目录保留Git原测试、E1当次未追踪helper、原launcher和开发fixture的字节；三个核心hash依次为 `f43ae42822cab11281e3a9b1d89c56e12d162a7582b32dfa679610563e58c467`、`5b1cf8b3dad34a2fde357cae21b8e57ed444bd38bec45c770c3e61f2e35846ef`、`2b7cdf5f5d7f42f23d4877c03f7d8c7e7867233127db7769d10cbf084ff7b91a`。执行使用当前候选中与基线相同的生产源码，不修改候选测试。R1重放是新的运行和日志，不冒充E1原运行。

真实工具进入设置为0.8秒的启动等待；原0.6秒请求在工具ready/executing之前正确超时，实际请求终态latency为693.6342ms。工具alive、starting=true、无结果，随后exit=-15、stopped/reaped/directory_cleaned=true；模型exit=0且回收。原前三个断言通过，最后operation_started断言仍失败，原始exit1保留。这证明启动前正常到期不应被判作执行器缺陷。

| 新完整CPU组内场景 | 真实工具阶段 | observation | harness终态 | 共用正向断言 |
|---|---|---|---|---|
| before-tool-start | alive，未executing，未blocking，无结果 | cancelled/cancelled/false；测试时钟700ms | timed_out | 通过 |
| inside-blocking-tool | 已进入原生产block分支，实际60秒sleep调用，无结果 | cancelled/cancelled/false；测试时钟700ms | timed_out | 通过 |
| bypassed-request-rejected | 同样进入阻塞分支 | timed_out/tool_timeout/true；测试时钟1100ms | timed_out | 明确拒绝 |

仅harness/executor/isolation各自的`time`引用使用父进程测试时钟；harness UTC remainder固定0.6秒，executor固定10000秒。全局time、真实spawn、生产block/IPC及停止/join未替换。真实门控前时钟固定，门控后0.7秒越过请求期限；只有工具wait继续真实轮询0.2秒才到1.1秒。700/1100ms是测试时钟，不能登记为性能。三个目标场景的实际时长分别约1.0185、1.0843、1.2862秒。

绕过请求约束的lambda仍保留外部caller cancellation。R1另用原负向launcher和候选两份测试字节执行不捕获断言的命令：工具靠原1秒上限收尾，harness仍timed_out，但同一断言在错误原因处失败，exit1。所有先行进程回收断言均通过；不能把这次重放或捕获预期失败的pytest PASS再累计为新增成功场景。

## 独立补充探针与清理

[两个补充探针](test_deadline_boundaries.py)均通过。第一项在已阻塞工具的真实close之前额外等待0.3秒；请求取消原因与700ms测试时钟保持，防止清理跨过0.2秒导致断言漂移。第二项使用真实子进程故意不产生门控标记，并绕过请求约束；测试时钟无法推进时，原10秒真实timer仍触发外部取消，实际10.1068秒退出，共用正向断言明确拒绝watchdog路径。

这两项直接记录真实Process对象的alive、实际close、句柄关闭和目录消失，并检查全部局部patch恢复与Timer线程消失。完整组三次、原失败一次、负向重放一次、补充两次合计7次运行、14个不同自有子进程：模型均exit0，工具均exit-15，全部reaped并清理自有目录；pytest的current符号链接未重复计数。原失败与负向控制的回收事实没有用伪造PID或记录替代。

## 实际验证与所有失败

| 命令组 | 结果 | 原日志SHA-256 |
|---|---|---|
| 完整CPU | 657 passed / 0 skipped，47.97秒 | `25d1ddbc82bb151a118c2f69d2e0a835f93bed5cb8c727594e239292931303ba` |
| 两个独立补充探针 | 2 passed / 0 skipped | `db7d9faf2e942cd19901409fe3e3a544ba65632fd57e468d9fed9a1a10c2a5ea` |
| 原测试慢启动重放 | exit1，预期原断言失败 | `c00c6a211a33097079dcdfe49289b223dfd8f8f40dedf324bd52bd0f70ed1e54` |
| 不捕获负向断言 | exit1，预期同一正向断言失败 | `1d3653bae64c5c2bc4909d937b9d6243aded91821e95b8ed2f7e80c7648db7ae` |
| 修正后的来源/证据核对 | exit0，全部4767路径 | `aab836534e008d39e9f548e416f5f15fb54bc9e0e66916e1dd42ece67f682729` |
| 修正后的归档核对 | exit0 | `5a959dbc05741685afa1e4bbcfd3ca85d922daa0fadc73d50dc7f14567df3913` |
| Ruff0.15.0 / 四契约冻结 | exit0 / exit0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` / `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| 暂存公开扫描 / 新探针显式Ruff | exit0，288路径 / exit0 | `94ee54afbd661585a1b1012f52940c1e5ed20ae20f572531fe6d6780199f8c31` / 同上Ruff hash |

657已包含三个目标场景、17项真实CPU tokenizer检查与既有P00/P01/P02/P03适用回归；补充两项单列。复用28包Python3.14.7纯CPU环境，禁写bytecode，无模型框架可用。完整命令如下，实际路径和全部argv私有绑定，四个R1临时目录都没有`.toolalign-local`祖先：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src TOOLALIGN_TOKENIZER_DIR="$TOKENIZER_SOURCE" "$CPU_PYTHON" -B -m pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py reports/review/P02/test_p02_boundaries.py reports/review/P03/test_p03_lifecycle.py reports/review/P03/test_p03_semantics.py reports/review/P01/test_p01_processes.py reports/review/P01/test_p01_failure_counters.py reports/review/P01-r2/test_p01_r2_regressions.py reports/hardware/P01_FIX_R3_REPORT_TESTS.py reports/hardware/P01_FIX_R4_REPORT_TESTS.py --basetemp="$R1_FULL_TEMP"
```

E1原四次有文件日志的失败均按原hash保留：旧断言及负向断言exit1；首次完整调用缺psutil导致收集exit2；第二次basetemp处于私有路径祖先导致旧P02测试未抛DataError，639 passed/17 skipped/1 failed。R1核对实际调用位置及原错误，未修改旧测试或来源规则；借用正确CPU环境后R1独立657全过。E1另有一次inline保全比较错误，只有交互输出，没有独立stdout文件；该限制保持，不虚构hash，正确清单的全量字节已重新核对。

R1两次辅助检查设置错误也保留原脚本与exit1日志：路径allowlist误拒绝历史venv解释器链接（`fd836a366dabb3f4b7e5767fc53406d4a5661e7df2dc31b3edbe8763b6b7f222`）；归档预期集合漏列自动包含的Git `.gitignore`（`8aef39951fff1cb5da9f712221c1962d791b5497a3892b76e84c594efeac63d8`）。修正路径解析及固定成员后逐项重核，没有删除原清单项或改候选。另一次只读历史helper文件名拼错未单独保存stdout，机器证据如实登记，不算候选测试失败。

## 实际归档、资源及限制

| 本轮实际产物 | bytes / 成员 | SHA-256 |
|---|---|---|
| 新sdist | 194485 / 89（88份Git载荷+PKG-INFO） | `eed6c038c31170a0fb4957b8286e01f20b0ecf96c64514f05f9b97a1040a76fc` |
| 默认wheel，由同次sdist生成 | 96713 / 47（42份生产载荷+5份metadata） | `e2c5d06beff3c8b7bc0098c0c58a45413de2dbd505ad5378acb05f689a7657b5` |
| 显式由新sdist重建wheel | 96713 / 47 | 同上 |
| 精确4a1包输入的直接wheel | 96713 / 47 | 同上 |

[归档检查](review_package.py)核对全部成员、路径/链接、Git字节、metadata和每条RECORD。新helper进入sdist，未进入wheel；没有额外私有载荷。基线使用45份精确4a1包输入Git blobs，三份wheel完全相同。四份本轮实际新构建文件与E1制品恰好同hash，但构建时间、命令与日志各自登记；候选没有额外直接源码wheel路线。未重装字节未变的生产wheel或重开旧安装边界审计。

公开前本轮私有根与四个pytest目录的实际保留文件共7030151 bytes，低于2GiB；该数是逻辑文件快照，不是峰值或累计I/O。源/包字节未变，未新增项目/模型环境、下载、模型/GPU任务或全量数据重测。公开扫描与提交后的实际commit/tree在最终私有命令索引及原生交接封存。

新候选GitHub CI、PR8最终组合/主干验证、Linux/Python3.11本机执行、训练/BFCL/正式评测、P04、模型/数据上传及服务部署均NOT_RUN；kris人审与G-DATA未代签。R1 PASS不替代S0的最终组合CI、集成和main验证。本轮提交后停止，等待S0。
