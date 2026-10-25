# P04 CUDA / Colab：S1 集成记录

2026-10-26。**CUDA/Colab CPU 实现已通过独立审查及S1定点集成，GPU未分配。** Q1的13例语义预审通过；E1 r3关闭最后一个控制问题，原失败保留。PR21合并仍须对应最终head的Linux CI通过；交接基线为 `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`。

## 候选与独立证据

| 范围 | 精确候选 / review | 结论 |
|---|---|---|
| CUDA SFT | `4342af87615197c7947d001f462d3d31500cd501` / `7d460f2054201c00055a1f924c5c4984be8e6988` | [R1 CPU PASS](reviews/P04_CUDA_SFT_R1.md) |
| Colab 控制 r2 | `172a462fc5f39283a3aea8b7d11062a3f8e7fcc6` / `65ffcc31dd51d2b54475a446c74015265e719b61` | [r2 FAIL](reviews/P04_COLAB_ENVIRONMENT_R2.md)：PROCESS-001未关闭，RECOVERY-001与跨session组合PASS |
| Colab 控制 r3 | `6183870587f349bf56945e0709ab1488737a2556` / `7825216a081f711e6da06ae440626193b7820ea2` | [r3 PASS](reviews/P04_COLAB_ENVIRONMENT_R3.md)：PROCESS-001关闭，计数归零，前两次FAIL保留 |
| 13例 mask 与说明 | `4342af87615197c7947d001f462d3d31500cd501` / `82f1e88e168b80298c47455c26084cc9a4b54b92` | [Q1预审 PASS](reviews/P04_CUDA_MASK_Q1_R1.md)，423项检查、26条原证据绑定 |
| T1/E1 r3组合 | `0eaad46e115d1296ce83cf22d5cc1f5aea86011c` | 独立复核与S1定点集成通过 |

## S1 实际检查

执行源 HEAD 为 `5b80ddf1cdf884d66af755f38bffd111e85929dc`，生产与组合提交相同。共享 Python 3.12 CPU 环境，OMP/MKL各2；每条命令由既有命令记录器保存 stdout、stderr、退出码和前后源码身份。全部命令期间源码未变。

| 检查 | 结果 | receipt SHA256 |
|---|---|---|
| 三个 CUDA 测试模块及 `tests/colab` | 42 passed / 1 failed，55.48秒 | `f24f2aab1b65201ebc65dac85d6987eeadef54fcac1493bcf2aff9e9b611d572` |
| 新增 CUDA/Colab 路径 ruff | PASS | `6adb72faaa85b8ced292cfce7a0f94128c8674d9864b5df95a0ff41fc3055bae` |
| 冻结契约 | PASS | `1485905370b27a173033c0475aabcd46a7152673e6855ec158cd106f9c73da4b` |
| 公开内容扫描 | PASS | `8b90a4a7cd95b2faf1361898e76aa4cc35c1d4c0b3429b29dc0998b5dd55b14b` |
| source distribution | PASS | `77931e332d264a5822e7e5af9e193fbe69f2b5fc176c401d449138c2aff04daa` |

失败项为 `test_timeout_cleans_same_group_descendant_after_leader_exit`。现场 `exit.json` 记录 `timed_out=true`、`timeout_cleanup_completed=false`、`error="[Errno 1] Operation not permitted"`；子进程在结束前仍写入 heartbeat。fixture 的 finally 随后清理了捕获的子进程，当前无该测试进程残留。原日志和现场保留，并交 R1/E1 定位；尚不能从该记录断言 EPERM 的具体系统原因。该检查不是新的实质修订，正式计数由独立 r2 裁定后更新。

R1随后独立诊断记录到 SIGKILL 发送成功，紧接着signal-0查询EPERM，后代已经消失。该证据将r2失败定位到完成确认；S1原现场没有记录具体调用位置，保持原边界。正式接收r2为PROCESS-001第二次未通过，RECOVERY-001关闭归零；原失败保留。

[草稿PR21](https://github.com/kris0516/ToolAlign/pull/21)首个head `f50216b45e446a045dced53cfe1d15b56ee7e124` 的 [Linux CI](https://github.com/kris0516/ToolAlign/actions/runs/40244485319)通过：Python 3.11与3.14的ruff、pytest、独立契约、冻结、公开扫描和分发检查均成功。该平台检查不抵销Mac的已观察失败，后续源码修订另验。

## r3 定点集成

E1修订实现为 `93a837e345856b1067d221f411b537b933fe7f89`，最终候选 `6183870587f349bf56945e0709ab1488737a2556`；后者仅新增报告与交接。生产改动为signal-0查询EPERM时继续使用既有有界确认，未修改实际终止信号发送路径；作者实际控制检查30项通过。R1在精确组合 `0eaad46e115d1296ce83cf22d5cc1f5aea86011c` 再次捕获同样的真实EPERM并通过原用例，新四项判别检查也通过；最终独立PASS为 `7825216a081f711e6da06ae440626193b7820ea2`。

S1在 `173f7b1082c5edd0329786cd8a834ce24b8cd6da`（生产与该组合一致）先导入共享CPU Torch，再运行新增四项边界检查和原真实同组后代用例：**5 passed / 13.69秒**。记录器exit 0、wall 15.51秒、源码前后不变；receipt SHA256为 `17c0e16ca505a610d0b65c9102311d1906952f8e188bc9e404e0d0ccf7743be4`。原42通过/1失败记录保留，未变的数值、依赖及恢复证据沿用。

20条容量数组尚未生成；实际 Linux安装、CUDA forward/backward/optimizer/validation、完整 checkpoint 新进程及新实例恢复、正式 SFT 和模型效果均 **NOT_RUN**。下一步按PR21最终CI与合并回执冻结源码，再生成与审核有界容量数组。
