# P04 CUDA / Colab：S1 集成记录

2026-10-26。当前为待审组合，**尚未通过全部集成检查，GPU 未分配**。T1 的 CUDA SFT CPU 实现及 Q1 的13例语义预审已通过；E1 r2 复审保留一项P1，r3定点修订中。主干仍为 `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`。

## 候选与独立证据

| 范围 | 精确候选 / review | 结论 |
|---|---|---|
| CUDA SFT | `4342af87615197c7947d001f462d3d31500cd501` / `7d460f2054201c00055a1f924c5c4984be8e6988` | [R1 CPU PASS](reviews/P04_CUDA_SFT_R1.md) |
| Colab 控制 r2 | `172a462fc5f39283a3aea8b7d11062a3f8e7fcc6` / `65ffcc31dd51d2b54475a446c74015265e719b61` | [r2 FAIL](reviews/P04_COLAB_ENVIRONMENT_R2.md)：PROCESS-001未关闭，RECOVERY-001与跨session组合PASS |
| 13例 mask 与说明 | `4342af87615197c7947d001f462d3d31500cd501` / `82f1e88e168b80298c47455c26084cc9a4b54b92` | [Q1预审 PASS](reviews/P04_CUDA_MASK_Q1_R1.md)，423项检查、26条原证据绑定 |
| T1/E1组合 | `ddc4aef8b332c5f30db84e84c29bd571a8439a0e` | 待完成复审与集成 |

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

20条容量数组尚未生成；实际 Linux安装、CUDA forward/backward/optimizer/validation、完整 checkpoint 新进程及新实例恢复、正式 SFT 和模型效果均 **NOT_RUN**。下一步完成r3修复复审，冻结精确源码，再生成与审核有界容量数组。
