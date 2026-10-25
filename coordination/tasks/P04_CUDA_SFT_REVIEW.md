# R1｜P04 CUDA SFT 独立复核

状态：READY。owner R1，协调者 S1。差异基线 `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`；先审核心提交 `6392f3c05c79bd808d93e6b89280acb650567692`，T1 的外部 SIGTERM 修复及最终报告提交由 S1 随后提供。authorization_commit 由原生消息给出。最终 verdict 必须指向最终精确候选，不能把核心提交的通过延伸为未读修复的通过。

目标：按 [T1 任务](P04_CUDA_SFT.md)和 [CUDA 协议](../../configs/sft-cuda.v1.json)独立验证可进入真实数据/Colab 验证的 CPU 实现。复用 R1 自己的干净 worktree，从核心提交建 `codex/review-p04-cuda-sft-r1`；先保存当前授权文件，保留前一 Colab 审查分支与私有历史。只新增 `reports/reviews/P04_CUDA_SFT_R1.md`、`coordination/handoffs/P04-cuda-sft-review-r1.md` 和本轮必要私有复现，不修改训练实现或配置/锁/共享状态。

核对冻结 v3/13例到 portable arrays 的身份、角色和 mask；一次 causal shift；completion+单 EOS、右 padding；每样本 token mean 再按实际累积组取 mean，尤其末批 7/2；验证总 CE/监督 token；Q/V LoRA 配置、底座冻结与 adapter dtype；标准 AdamW、固定 LR；完整 optimizer/RNG/cursor 和身份拒绝；best/last/rollback；CUDA-only 与共享 GPU 租约；有界父子进程及外部 SIGTERM 清理。使用独立手算或原创小 tensor 验证关键数值，不用复制实现逻辑作为 oracle。

复跑新增定点测试及必要独立检查；未变的旧 163 项与数据准备证据沿用。依赖锁可读取 E1 精确候选 `8faa75e7010290a11f13a8006fba5d4b16ac44f9` 中的锁，仅做接口核对；E1 控制代码另有两项已登记 P1，不能由此审查批准。S1 的跨 session 小型 CPU 复现已提供给 T1，作者正修复；核对最终修复并实际检查外部终止后的子进程状态。

使用 S1 唯一共享 Python 3.12 CPU 环境，路径由原生消息给出，`PYTHONPATH` 为 R1 自己的 `src`；OMP/MKL 各 2。原创 fixture 参数至多4096、序列至多16、每次更新至多3；单命令至多300秒，新增私有证据至多200MiB。pytest 每次用新独占 basetemp。真实数据 prepare/新编码、模型加载/下载、GPU/SSH/真实训练均为0；实际20例数组与Q1、CUDA容量/新实例恢复由S1后续执行。

交付 PASS/FAIL/BLOCKED、精确 reviewed SHA、实际命令/退出码、重要数值和失败记录、未验证项；阻断项给最小复现和稳定 issue ID 建议，不代修作者代码。已知待修部分可先记录，等待 S1 提供最终候选后一次正式裁定；同一候选重读不增加正式修订次数。通过后仍需集成、真实数组与GPU验证，不能用CPU toy代替模型实测。
