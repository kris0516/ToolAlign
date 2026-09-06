# P03-ci-deadline-r1｜E1 交接

2026-09-06。**工作者修订与自查已完成，待独立 R1 对完整候选复核。** 本轮解决已有 deadline 测试对 spawn 启动速度的未保证假设；没有更改已验收的 P03 生产实现，也没有宣布最终 CI/main 验收通过。

| 字段 | 值 |
|---|---|
| owner / 模型 | E1，原独立任务 / gpt-6-astra、max |
| authorization_commit | `fa1ea86361223171a06b5d082a3731b63a00a74a` |
| branch / base | `work/p03-ci-deadline` / `4a1fa84d2d367ed037a1e39b1d4033f54a385e6a` |
| 精确实测代码提交 / parent | `f69c6a309ff45980c21c2119016f4c5cf8acf8b7` / 上述 base |
| 代码 tree | `9c637b38f3155551e4d8b73b76db1ce0a53c3639` |
| 契约 | plan-v0.1 / coordination.v1 / toolalign.contracts.v1；冻结保持 |
| 正式证据 | [验证报告](../../reports/harness/P03_CI_DEADLINE_VERIFICATION.md) / [机器证据](../../reports/harness/P03_CI_DEADLINE_EVIDENCE.json) |

完整交付包含实测代码提交及随后仅三份文档的提交；准确的完整 SHA/parent/tree、普通 push 与远端读回在 S0 原生交接及本机私有 manifest 按实际结果登记。文档不在 sdist 载荷中，不改变已验证测试、依赖、源码或包输入。

## 授权范围内的交付

1. `tests/evaluation/harness/test_harness.py` 仅替换原目标测试为三个具名场景，保留 wire/预算/真实进程回收断言，并核对请求取消的实际工具 observation。
2. 新增 `tests/evaluation/harness/deadline_cases.py`：本测试局部的真实 spawn 启动门、生产阻塞分支标记、测试时钟及独立有界退出。全局时间模块与生产源码未改。
3. 新增本交接、验证报告、机器证据。没有修改其他测试、旧审查/报告、依赖/配置/CI、协调状态或其他 worktree；没有新任务/sub-agent。

原失败在精确4a1及原测试字节上独立复现：0.8秒受控启动超过0.6秒总请求预算，工具尚未执行时请求真实约704.64ms正常到期，真实工具进程 exit=-15 并回收；旧 `operation_started` 断言仍失败。原日志 `110f7f434feb77fe2ea096f31eb1b1608c957a025c48112f66aaf346cc68fedd` 和当时未追踪 helper/私有 launcher 原字节已在修改前封存；没有回标未来提交，也未重复该失败。

新场景明确区分启动前与阻塞后到期；父时钟0→0.7→1.1秒与 UTC remainder=10000 为测试替身，真实子进程及回收没有替身。正常控制在请求期限后、工具期限前以 cancelled observation 退出；仅绕过请求单调约束时，真实工具继续到自身 tool_timeout，虽然最终 harness 仍 timed_out，共用正向断言明确失败。不捕获该断言的实际负向命令 exit1，日志 `248d9bf09baf52331867791ff17ce8dc1d12d1ed0e33b390c194114dfb17274b`；10秒外部取消 watchdog 与原工具期限独立有界，实际未触发 watchdog。

## 复核所需实测

- 精确f69完整 CPU **657 passed、0 skipped**，48.04秒；包含17项只读固定 tokenizer、三个 deadline 场景与原适用独立审查。原日志 `1fa81e480d9e787753593260df074b7a5b4457ed6c75ddc5fe48dd67b91f7f01`。命令、实际环境与各来源 hash 在正式证据中绑定，不沿用S0测试结果。
- Ruff、四契约冻结、代码提交279路径公开扫描均通过；文档提交后执行最终公开扫描，结果另回报S0。
- 实际新 sdist 为194485 bytes，SHA `eed6c038c31170a0fb4957b8286e01f20b0ecf96c64514f05f9b97a1040a76fc`；89成员中88份当前Git字节加1份metadata，含新helper。
- 实际默认/显式sdist重建/精确4a1基线直接 wheel 均为96713 bytes，SHA `e2c5d06beff3c8b7bc0098c0c58a45413de2dbd505ad5378acb05f689a7657b5`，三份逐字节一致；42份生产载荷加5份metadata，未变安装路径不重复扩大。
- 277份原基线路径和1818件旧私有证据/归档保持；原两refs未改。新测试 SHA `af310542d8bcf5aad86f54bcac6487d2be225f20ebc06e8eb692254eeedf0850`，helper SHA `0b121de0d3b65b3ba5078b28556cbd17592a2ac7ef6f48c421bd94dd46be4046`。

所有失败保留：旧断言复现、有效负向断言；首次完整调用缺psutil导致收集exit2；第二次E1将basetemp放在私有命名空间内导致旧P02路径测试setup失效（639 passed/17 skipped/1 failed），只改调用位置与复用S0已授权的纯CPU环境后657全过；另有辅助保全核对将manifest对象误比hash字符串的inline exit1，只修字段读取后1818件全部保持，该次原输出未单独落日志，未虚构hash。详见报告与机器证据，不删旧测试/记录，不新增skip/xfail。

新增制品为约21MiB的本轮私有制品与系统pytest目录，远低于2GiB；实际路径只存本机。借用CPU环境不写bytecode，5份tokenizer来源hash前后保持；未导入模型框架、下载模型、占GPU或产生费用。

## NOT_RUN 与下一步

新模型格式、模型框架/真实模型harness、训练/正式评测/BFCL、推理服务、候选GitHub CI及本机Linux/Python3.11均NOT_RUN。只普通推送本轮新分支；原P03/格式分支与main不改。提交回报后停止本轮实现，等待R1独立复核；S0随后决定与已审格式的集成及最终CI/main验证。
