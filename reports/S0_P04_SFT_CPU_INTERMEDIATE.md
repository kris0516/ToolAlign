# P04-SFT-CPU 中间证据与上游 CPU 入口限制

2026-09-06，S0。本记录核对 T1 正在进行的 CPU 实现证据；完整候选、独立 R1、最终 CI 和 main 集成尚未完成。原授权 `e42536dd7c77d90ed33ab5354f288ab0f1c3d6c6`、基线 `42eaa50a9519efe96d60b49f07cfbd106b36778c` 与配置 SHA-256 `5aad6ff6db68ee4fe9bac0aa6104eaeff17bf948b509bfce3d14e3eac9d9aa29` 保持。

## 已核对的实际结果

首次执行提交 `96fcbe1f34fc9d2afe1d9faf3935817d37b22d76`，tree `a64b9febee9d541a92c3a7e692aa149b264beadf`。13 例新 collator 命令实际于 15:15:53–15:17:22 UTC 运行，退出 0；仅增加一遍 10 条已选 train 和 3 条单列原创协议例的 native 编码。没有新增全量编码、数据选择物化或参考 tokenizer 测量。

S0 于 15:27:02–15:27:07 UTC 直接核对新输出与既有 native、reference、人工副本的全部 13 例 JSON：Example、原序列、padding、unshifted/next-token token IDs、attention/loss mask、首末监督位置和分母一致；另从完整数组重算位移、EOS 与有效监督区间。包括实际最长 2048、1536 边界及非 ASCII 例。协议例在原命令中保持为单列输入。

原准备命令已运行两份 selection verifier，读取四个 train/validation 视图；其数量/身份与已验收 manifest 对应：smoke 为 1600/197，formal 为 6013/217。计划为 smoke 200 次更新、formal 751 个完整累积周期加 5 微步尾周期，共 752 次更新；**这些是计划数量，实际模型训练次数为 0**。

S0 共核对 164 个当前文件路径，另将两个历史执行提交各 378 份源码快照与相应 Git blob 对齐。86 份原 selection/native/reference 文件同时匹配先前 R1 已核对的原 hash；人工材料及两份填写 CSV 保持原记录。私有证明 SHA-256：`42d0eb64846943c440f6f468aceea55f56af264701bcb226c037d39dd852960d`。S0 本次没有重跑 tokenizer 或框架数值流程。

## 两次真实失败及有效边界

| 回放 | 执行提交 | 实际结果 | 墙钟 / 峰值 RSS |
|---|---|---|---|
| 首次 segmented | `96fcbe1` | 检查器误将 DLPack 的 `(8,0)` 当成非 CPU 执行，断言失败，退出 1；未进入 MLX 训练循环 | 6.272 秒 / 388268032 bytes |
| segmented-r2 | `9e71552c22b4ed5daf4e4a66e24816bd61f53092` | 修正设备证据后，未修改的 MLX-LM `train` 在入口读取缺失属性，抛出 `KeyError: max_recommended_working_set_size`，退出 1；未进入训练循环 | 2.864 秒 / 389775360 bytes |

两轮分别于 15:16:12–15:16:18、15:18:30–15:18:32 UTC 执行。每轮在导入框架前实际取得共享租约，设 CPU 默认设备；子进程终态保持租约直到退出。监督记录证明两进程回收、PID 已不存在、锁释放；S0 再次检查两 PID 均不存在，15:27 UTC 共享锁空闲。原失败、stdout/stderr、环境、开始/结束记录及源码快照全部保留。

`9e71552` 只修正新检查器的设备证据。MLX v0.32.2 的 DLPack 接口在 Metal 可用时直接返回 `(8,0)`，不能据此判断运算设备；本轮记录的默认设备和 CPU stream 均为 CPU。[官方 array.cpp](https://github.com/ml-explore/mlx/blob/v0.32.2/python/src/array.cpp#L499)

已锁定的 MLX-LM 0.31.3 `trainer.py`（SHA-256 `ee33ebdbd20a184108541cb490d08085485e71a82ffd6d68d7d216029ecd28fe`）在进入训练循环前，若 Metal 可用就调用 `mx.device_info()["max_recommended_working_set_size"]`。MLX v0.32.2 的无参 `device_info()` 查询当前默认设备；CPU 返回值不提供该 Metal 属性，本轮原始 traceback 在该语句失败。公开 loss/iterator/TrainingArgs 注入点尚未执行。[官方 device.cpp](https://github.com/ml-explore/mlx/blob/v0.32.2/python/src/device.cpp#L78)

第二轮在该失败前完成了 13 条原创、词表 8、参数 64 的 CPU loss/gradient 对照：报告的最大梯度绝对差为 `4.470348358154297e-08`，loss 差、右 padding 的 loss/gradient 差以及被忽略预测位置的 logits 改变后的 loss 差均为 0。上游 default_loss 在原创例多计一个 token（3 对 2），CE 为 2.0883114337921143 对正确值 2.074565887451172。此处记录已有实际数值输出及源码绑定；尚无独立 R1 回放。该例证实 padding 缺陷，不替代训练更新验证。

两轮 actual MLX optimizer 更新均为 0；第二轮独立 Torch 参考曾执行两次原创小更新，不能记为 MLX-LM 成功。8+5 尾周期、actual train 的最终参数、保存/重载、post-tail validation 和 best/last checkpoint 绑定仍为 **NOT_RUN / 上游入口阻塞**，没有正式 SFT checkpoint。

## 当前接续

S0 已向 T1 反馈实际入口反例，按原任务包的上游限制分支继续其余 CPU 语义测试、默认接口、真实构建/安装及完整交接。保留 CPU 默认设备，不修改 vendor、不通过 monkeypatch 或切换 GPU 默认值跨过入口；本记录没有扩大原授权。待精确候选与失败清单交付后安排独立 R1，按实际完成范围决定后续兼容修订。

100 行数据语义填写副本与 13 行 token/mask 填写副本仍各为 0 reviewer / 0 verdict，实际材料页面观察为 0 页。原浏览器拒绝保持，不绕过。G-DATA、P04 正式训练和真实模型容量门槛均未关闭；P00–P09 整体目标未完成。
