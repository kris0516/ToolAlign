# P03-CI-DEADLINE｜请求截止时间测试修订证据

2026-09-06，E1。**本轮测试修订自查通过，等待精确候选的独立 R1 复核。** 实际完整 CPU 检查为 **657 passed，0 skipped**；新生产 wheel 与精确基线重新构建的 wheel 字节相同。尚未运行本候选的 GitHub CI，不能据此宣布 PR8 或最终集成通过。

## 提交与边界

| 项目 | 精确值 |
|---|---|
| 授权 | `fa1ea86361223171a06b5d082a3731b63a00a74a` |
| 新分支 / code_base | `work/p03-ci-deadline` / `4a1fa84d2d367ed037a1e39b1d4033f54a385e6a` |
| 实测代码提交 / parent | `f69c6a309ff45980c21c2119016f4c5cf8acf8b7` / 上述 code_base |
| 代码 tree | `9c637b38f3155551e4d8b73b76db1ce0a53c3639` |
| 契约 | plan-v0.1 / coordination.v1 / toolalign.contracts.v1；均未变 |
| 实现差异 | 仅目标测试及新增 `tests/evaluation/harness/deadline_cases.py` |
| 随后交付文档 | 本报告、[机器证据](P03_CI_DEADLINE_EVIDENCE.json)、[本轮交接](../../coordination/handoffs/P03-ci-deadline-r1.md)；不改变测试或包输入 |

277 份基线文件保持，唯一变化的既有文件是目标 `test_harness.py`。所有生产源码、其他测试、原审查/报告、配置、依赖锁、CI 和协调状态未改；未合入未验收格式或后续 main。原本地 P03 分支仍为 `3598cef2efb99e2990e384812a028902964cf494`，原 remote-tracking ref 仍为 `84084770bf07f32647af36ac748bf76326e74ed1`；未推进旧分支。完整文档交付提交及实际远端读回另按真实 Git 对象回报 S0，不把后续提交倒填为早期运行的 HEAD。

## 旧失败的独立复现

[CI34024093376](https://github.com/kris0516/ToolAlign/actions/runs/34024093376) 在 Python3.14.7/Ubuntu24.04.4 上为 1 failed/484 passed/48 skipped；该失败的三个前置断言已通过，最后要求工具 `operation_started=true` 时失败。四份基线文件与失败候选完全相同，原 decoded job log SHA-256 为 `81931c5cd7ba3fe8c8cfa1aa4dc172220682c28ed2247359422b584092225013`。

在 HEAD=`4a1fa84`、目标测试原字节未改时，私有 launcher 调用原测试，并用当时**未追踪**的 helper 给真实 spawn 工具子进程加入 0.8 秒启动等待。模型与工具仍由原 `OwnedProcess` 创建和回收；没有改生产源码或模拟返回结果。原测试的总预算仍为 0.6 秒。

实际终态为 `timed_out`，真实 latency=704.6436ms，1 model decision/1 tool round，已知 input/output tokens=11/7。工具回收前确实 alive、已进入启动 helper、未 ready、未 executing、无 result；随后工具 exit=-15、stopped/reaped/directory_cleaned 均 true，模型 exit=0/reaped，未留自有目录。旧测试在同一 `operation_started` 断言失败，exit=1。该反例证明预算可以在工具执行前正常耗尽；没有据此登记生产 deadline 或回收缺陷，也未重复原失败来等待偶然通过。

| 原始来源 | SHA-256 |
|---|---|
| 原 `test_harness.py` | `f43ae42822cab11281e3a9b1d89c56e12d162a7582b32dfa679610563e58c467` |
| 该次未追踪 helper 的原字节，修改前已封存 | `5b1cf8b3dad34a2fde357cae21b8e57ed444bd38bec45c770c3e61f2e35846ef` |
| 该次私有 launcher，保持原字节 | `2b7cdf5f5d7f42f23d4877c03f7d8c7e7867233127db7769d10cbf084ff7b91a` |
| 实际失败原日志 | `110f7f434feb77fe2ea096f31eb1b1608c957a025c48112f66aaf346cc68fedd` |
| 新 `test_harness.py` | `af310542d8bcf5aad86f54bcac6487d2be225f20ebc06e8eb692254eeedf0850` |
| 新 `deadline_cases.py` | `0b121de0d3b65b3ba5078b28556cbd17592a2ac7ef6f48c421bd94dd46be4046` |

## 新测试实际验证的边界

保留原 0.6 秒请求预算和原 executor `utc_remaining=10000` 替身。父进程的三个模块使用局部测试时钟：在真实 spawn 与门控期间固定为起点，实际目标阶段出现后前进至 0.7 秒。请求期限为 0.6 秒，原工具上限为 1 秒；不再要求操作系统在请求预算内完成两次 spawn。全局 `time` 模块、子进程真实等待及生产执行/回收代码未替换。

真实工具子进程先延迟 0.8 秒。启动前场景在 ready 门处保持；阻塞场景释放门后调用原 `_tool_child`，其原 `fault="block"` 分支进入被记录的真实 sleep。阶段记录包含当时实际 PID/alive、executing/blocking 标记与无结果状态；停止与回收仍调用原进程对象，原 `assert_trace` 继续检查合法 trace、预算单调和自有 PID 不在 active children 中。

若请求约束被绕过，工具 wait 继续轮询满 0.2 秒真实时间后，测试时钟前进至 1.1 秒，由原 per-tool timeout 独立结束。该前进仅在继续轮询时发生，正常取消后的 join/清理耗时不会改变断言时钟。另有独立 10 秒真实 timer 取消调用方 token，finally 取消并 join timer、关闭所创建的进程；这三个实际场景中 watchdog 均未触发。

| 完整 CPU 组内的实际场景 | 工具已执行 / 阻塞 | 工具 observation | harness 终态 | 共用断言 |
|---|---|---|---|---|
| 启动前耗尽预算 | false / false | cancelled / cancelled / retryable=false；测试时钟700ms | timed_out | 通过 |
| 已进入生产阻塞分支后到期 | true / true | cancelled / cancelled / retryable=false；测试时钟700ms | timed_out | 通过 |
| 仅绕过请求单调取消约束 | true / true | timed_out / tool_timeout / retryable=true；测试时钟1100ms | timed_out | 明确拒绝 |

三场景每次各有一个模型和一个工具真实子进程；模型 exit=0、工具 exit=-15，均已回收并清理目录。负向控制保留外部 cancellation 和原工具上限，其终态同样 `timed_out`，所以新断言同时核对 observation 的取消原因及其先于工具期限，避免把晚到的 per-tool timeout 当作请求约束生效。负向控制另以不捕获断言的私有命令实际运行为 exit=1；公共测试用 `pytest.raises` 精确匹配这条失败，不接受 setup/watchdog 等其他异常，也未新增 skip/xfail。

测试时钟的 700/1100ms 不是性能测量；原总 latency<1500ms 断言由更明确的“请求原因取消且 observation 在工具期限之前”替代。CPU scripted backend、UTC remainder 与父时钟的替身范围均如实记录，未声称实际 UTC 系统时钟被修改或真实模型兼容性得到验证。

## 完整检查及全部失败记录

原正负控制先在 HEAD=`4a1fa84` 的未提交工作树运行；两份新文件的 hash 与随后 `f69c6a3` 一致，已单独绑定。其余完整检查与归档绑定精确 `f69c6a3`。

| 实际检查 | 退出码 / 结果 | 原日志 SHA-256 |
|---|---|---|
| 原测试 + 受控慢启动 | 1；预期旧断言失败 | `110f7f434feb77fe2ea096f31eb1b1608c957a025c48112f66aaf346cc68fedd` |
| 三项正负控制 | 0；3 passed | `04abbde499bc1bea6ae1b68a1efa521c15addbb6b24302b4a9db439fcd656f61` |
| 不捕获负向断言 | 1；预期拒绝 | `248d9bf09baf52331867791ff17ce8dc1d12d1ed0e33b390c194114dfb17274b` |
| 首次完整调用 | 2；旧 P01 审查缺 psutil，收集停止 | `2a8de6e0e4827e37d07a5db0d4cea623e96fcf3370223bd33bab9afe080b65a7` |
| 单项 CPU 支持 | 0；按现有 uv.lock hashes 离线 target 安装 psutil7.2.2，无新环境或锁变更 | `07c6a34a2142959f9101c85436ddb40ef8853dbd4f6064282f3149ddba4117db` |
| 第二次完整调用 | 1；639 passed/17 skipped/1 failed，E1 的 basetemp 位置错误 | `fe4b278964a5bcdaca7c1beac780869c5a7af7d0f09e4d49d9e0ef551f7f3529` |
| 最终完整 CPU | 0；657 passed/0 skipped，48.04s | `1fa81e480d9e787753593260df074b7a5b4457ed6c75ddc5fe48dd67b91f7f01` |
| Ruff / 冻结 | 0 / 0；四契约文件未变 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` / `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| 代码提交公开扫描 | 0；279 paths | `ab18e42bb051cf03aa8c3d2a4e2286b633d25c02d522fc117e651697652fa4c0` |
| 实际 sdist + 默认 wheel | 0 | `be888e205d5c4c6292e7860ebc0c9d42f51ffe49e8045150444e12977ba6162a` |
| 显式 sdist 重建 wheel | 0 | `83628e343ff5b6f0a0a9592a34e9e58badacd23e1e65ce86f0419cf615936aeb` |
| 精确基线包输入直接 wheel | 0 | `6af6b6cbdd84f6768b56c736d2503b99a4175c5245a0b29e7432e182d10dd72a` |
| 归档当前 Git 载荷与基线对照 | 0 | `b2a2409acc8c0b25913aa4c95da3e358f5239ced1ff4ac4f661bdbf0bd46af3f` |
| 修正后的旧证据保全核对 | 0；1818 件 hash/bytes 均保持 | `efe9830ac7393f54b9fd15622c6a5aa940ddb790b86ca7ab27b7f5132b676c45` |

第二次完整调用的 `.toolalign-local` 祖先使旧 P02 测试拟造的 public 输出也满足私有路径政策；这是 E1 的调用设置错误。仅改用系统私有临时目录，不改该测试或生产路径规则。最终经 S0 授权只读复用既有 28 包纯 CPU 解释器及固定 tokenizer，禁写 bytecode，5 份来源文件前后 hash 保持；17 项真实 CPU tokenizer 检查实际执行。657 已包含三场景及原 harness/工具生命周期、P00/P01/P02/P03 适用独立检查；相对原655项增加2项，分组运行不再重复相加。

辅助保全核对另有一次 inline exit=1：E1 错把 manifest 的 `{sha256, bytes}` 对象直接与 SHA 字符串比较，导致全量误报，未写旧文件。原输出仅保留在本轮交互结果，未单独落 stdout 文件，故不虚构其日志 hash；原因和实际调用已登记在机器证据。修正为逐项读取两个字段后验证1818件全数保持，未删除任何比较项。原失败 helper、launcher、旧日志/归档和所有早期轮次保持原字节。

最终完整命令如下；三个路径变量的实际绝对值与完整 argv 私有绑定，`P03_PYTEST_TEMP` 必须不含 `.toolalign-local` 祖先。全部其他实际 argv、HEAD、tree、起止信息和日志 hash 见机器证据。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src TOOLALIGN_TOKENIZER_DIR="$P03_TOKENIZER_DIR" "$P03_CPU_PYTHON" -B -m pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py reports/review/P02/test_p02_boundaries.py reports/review/P03/test_p03_lifecycle.py reports/review/P03/test_p03_semantics.py reports/review/P01/test_p01_processes.py reports/review/P01/test_p01_failure_counters.py reports/review/P01-r2/test_p01_r2_regressions.py reports/hardware/P01_FIX_R3_REPORT_TESTS.py reports/hardware/P01_FIX_R4_REPORT_TESTS.py --basetemp="$P03_PYTEST_TEMP"
```

## 实际包字节与资源

| 产物 | Bytes / 成员 | 当前 Git 载荷 / metadata | SHA-256 |
|---|---|---|---|
| 新 sdist | 194485 / 89 | 88 / 1 | `eed6c038c31170a0fb4957b8286e01f20b0ecf96c64514f05f9b97a1040a76fc` |
| 默认 wheel，由同次 sdist 生成 | 96713 / 47 | 42 / 5 | `e2c5d06beff3c8b7bc0098c0c58a45413de2dbd505ad5378acb05f689a7657b5` |
| 显式从新 sdist 重建 wheel | 96713 / 47 | 42 / 5 | 同上，逐字节一致 |
| 精确4a1基线的直接 wheel | 96713 / 47 | 42 / 5 | 同上，逐字节一致 |

归档成员集合、路径/链接和当前 Git 字节全部核对，无未追踪载荷、缺失或差异；新测试 helper 确实进入 sdist，未进入 wheel。42 份生产源码/资源与基线保持。由于历史 P01 验收后 README 已变更，基线对照实际取4a1的45份包输入 Git blobs，未以较早、不同 metadata 的 wheel 充当当前基线。冻结 schema SHA-256 仍为 `ce17b0a5bc4e8363e1d67bf125212444bab1103ddfc0c4e390bef82afce881cb`。

09:50 UTC附近的实际磁盘快照：本轮 worktree 私有制品11972KiB、外部 pytest 临时制品9288KiB；既有复用 `.venv` 为35068KiB，不计作新增环境。新增制品远低于2GiB。仅 CPU，无新增 GPU/费用/下载；没有清理无关进程或修改其他 worktree。

本轮未重装字节完全相同的生产 wheel，未重复未变的共享归档边界调查；新模型格式、模型框架导入/加载、训练/BFCL/正式评测、Linux/Python3.11本机执行、独立R1、候选GitHub CI、main合并与服务部署均为 **NOT_RUN**。
