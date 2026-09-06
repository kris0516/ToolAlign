# P04 原生 toy：精确候选交接核验

日期：2026-09-07；状态 READY_FOR_REVIEW。T1 已实际普通推送并结束原生任务；S0 已核验完整候选与原始制品。独立 R1 尚未给出结论，未进行本包最终 CI/main 验收。

| 项目 | 实际身份 |
|---|---|
| 候选 | `f7326d1823c4cf132ae44525f4755c96c88ec159` |
| 唯一 parent | `c06782a61857259097932078c661189b4fda781d` |
| tree | `247eba004d714def81f0bef65375ddbf0fee95cf` |
| 代码基线 | `50867c0be43d110df6c3620c94022fcfdaf779b5` |
| T1 授权 | `de86568d73ee77bbf92b6f749a39a9ab38955836` |
| 分支 | `work/p04-sft-native-toy`，远端逐字一致，本地干净 |
| 原生终态 | 原轮 completed/idle；19:20:31 UTC 结束 |

候选仅改变 9 条授权路径：2 个既有 SFT 文件、7 个新增文件。408 份候选当前文件与精确 Git blob 相同；最后提交只加入报告、统计和交接，生产代码仍为 fae3d60。完整 [T1 交接](https://github.com/kris0516/ToolAlign/blob/f7326d1823c4cf132ae44525f4755c96c88ec159/coordination/handoffs/P04-sft-native-toy-r1.md)、[报告](https://github.com/kris0516/ToolAlign/blob/f7326d1823c4cf132ae44525f4755c96c88ec159/reports/experiments/P04_SFT_NATIVE_TOY_REPORT.md)和[统计索引](https://github.com/kris0516/ToolAlign/blob/f7326d1823c4cf132ae44525f4755c96c88ec159/reports/experiments/P04_SFT_NATIVE_TOY_VALIDATION.json)由原 SHA 保留。

S0 的[源码中间核验](S0_P04_SFT_NATIVE_TOY_INTERMEDIATE.md)确认原 534445b 两次实际 GPU 数值及 fae3d60 监督器终态修复。新增安装版核验于 19:10:17.601976–19:10:19.889377 UTC 实际完成：400 个当前/冻结路径、122 成员 sdist、两份各 63 成员 wheel、58 个包载荷对 Git、metadata、license、entry point 与完整 RECORD；15 条原默认安装命令和 9 个 SFT 来源，以及第三次实际 GPU 运行的全部 30 个模块来源均绑定安装 target。安装版完整 13 例数组、两份 Torch 状态、两个 checkpoint 文件字节、score 与重载结果同已审源码完全一致。新增 S0 framework/build/install 均为 0。

安装版实际 wall 为 3.407458584057167 秒、峰值 RSS 402309120 字节、MLX peak 5864 字节，实际进程已回收、PID 不存在、共享锁释放；最终诊断错误为空。原 stderr 仍有 semaphore shutdown warning；只对该原确切名称只读检查得 ENOENT，不宣称全局泄漏检查。

| 证据 | SHA-256 |
|---|---|
| S0 安装版/归档证明 | `42cca709273eb499dacbf8913e08f348e36d6c617abd48eebd18d970992a30f6` |
| S0 原命令/测量封存证明 | `224a14473e3bf79a61b33718697a983600251c4b6f95ee38b80f6c595dfce198` |
| S0 最终候选交接证明 | `b3b3e5b54abcc451f76e8731d72e00b516373b2f3f297abcacfabc0a48082f26` |
| T1 delivery | `e3145eafd84eef3a8f316f8fb8a4f4a124b4a6662ca12796987fc0365bc9203b` |
| T1 FINAL_FILES 清单 | `5a266eac20dd5e44db90b23711ca580b624d7cf071462c6da0e6fac6056eb1e0` |

测量封存核验实际检查 4980 个路径，包含 3016 份测量文件、1559 份旧私有文件、399 份不变基线；这些集合有重合，不能相加充当独立样本数。27 份原测量命令、7 个实际源码快照和 409 个源码 blob 均直接核对。3 次提交前 guard 的实际 HEAD/UTC 与不同工作区字节保持；其中一个未提交版本的重构 blob 仅在与原始回执 hash 完全一致后用于源码恢复，并明确标记，未冒充重跑。最终 CPU 五组实际 931+60+2+13+44=1050 passed、2 HF-only skips；新 36 项已包含，110 subtests 另记，所有原失败保留。

最终交接核验于 19:22:17.128053–19:22:18.549555 UTC 通过，检查 3456 当前路径、3038 份最终封存文件及 197 个 symlink 原目标字符串（不跟随链接）。清单前实际新增私有字节为 32235003，最终总量仍小于 2 GiB；旧两个工作分支、原 R1 CPU PASS 与 1559 份旧制品保持。31 份本轮原命令日志被直接核对；后 4 份为 3 个最终文档检查和实际新分支 push，push 确实运行于最终 f7326d1，其余 3 个检查运行于 c06782a 的最终文档工作区。

第一次 S0 最终核验辅助脚本错误要求上述 4 条命令都使用 parent HEAD，在实际 push 回执处失败；原脚本与日志保留。修订后的新目录核验逐命令使用实际 HEAD/tree，没有修改 T1 记录或重跑训练。最终证明的脚本 SHA-256 为 `3098867b5785d07cddbcc1ccb2a4d9550ca4733b73e5713dd362b130364d56ad`，exit 0、stdout SHA-256 `f943c66715d2c25cc27a0303f78da36e578c7eda410a707496fca31415fc8463`、stderr 为空。

本轮共 3 次实际 framework 启动：两次 segmented PASS、一次 unsegmented EXPECTED_NEGATIVE。原固定 13 rank/12 种数值载荷、64 参数和 44 个验证监督 token 保持；这不是模型质量或泛化验证。后续独立 R1 由[精确审查任务](../coordination/tasks/P04_SFT_NATIVE_TOY_REVIEW.md)另定边界，不借用 T1 余量。

原 CPU 上游 KeyError 仍有效。实际页面、kris 语义/token-mask 人审、真实模型容量、baseline/SFT/DPO、正式评测和部署均未完成；training_authorized=false，完整 P04 与 P00–P09 不因本候选交接而完成。
