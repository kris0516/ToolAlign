# P05-g4-dpo-r1 交接

E1 已完成 [原生 TRL DPO CPU 包](../../reports/P05_G4_DPO_CPU.md)，待 S1 回读与 R1 独立技术审查。基于 `f72bb5fc7343989efcfc01b305e690d0cddeb661`；S1 在 `421cda11c1cd8b8cf606faf19dc46de0d9abc5f3` 解除控制器保留后才编辑。精确交付 commit 及全部命令证据位于本 worktree `.toolalign-local/p05-g4-dpo-r1/handoff-index.json`，最终回复提供可点击入口。

交付范围：

- `cuda_dpo/`：D1/Q1 六文件输入绑定、冻结原始文本与 token 检查、独立双 SFT adapter 加载、原生 DPOTrainer、完整原生 checkpoint、CUDA-only 有界进程监督。
- `configs/dpo-cuda.v1.json`、独立 DPO Linux/Mac Python3.12 完整 hash 锁及 `.in`；保持原 SFT 直接依赖，仅既有传递依赖 fsspec 调整为2025.10.0，其余新增依赖详见报告。
- `scripts/colab/remote.py`、`support.py`：固定 DPO 白名单、专用环境与锁、显式安装索引及对应预算。现有 `control.py` 无需变动。
- 三个训练测试文件、两个原创 CPU fixture 支持文件、一个 Colab 测试文件，以及报告与本交接。

3项原生 CPU 验收均通过：独立逐 token/mask/SUM/sigmoid/梯度、初始ln2及仅policy adapter更新、10对8+2尾组和完整保存后新进程恢复。连续与恢复的adapter/Adam/尾梯度实际差值均为0，scheduler/RNG一致。Python3.12输入/进程/全部Colab控制回归70 passed；最后边界增补定点1 passed；Python3.14新接口29 passed/1 skipped，唯一缺pip parser的检查在3.12环境通过。全仓Ruff、4文件契约、846路径公开扫描、241项私有canary的源码/wheel打包检查及diff check通过。原失败记录保留。

给 S1/R1 的接口要点：

- 正式输入必须重新通过 D1 `apply_review`，并绑定 Q1 接纳的清单、lineage、原分母与六文件hash。`bind-input`/`prepare` 不授权训练；真实格式 CPU fixture 不构成真实Q1审核。
- 原始 chosen/rejected Action JSON 不重新序列化。冻结 renderer/tokenizer 的分别/拼接编码、EOS及原生TRL prepared IDs逐项核对；超长排除保留原分母，零有效对拒绝训练。
- policy/reference 均从固定 G3 step743 初始化；reference 全冻结、adapter启用，两个模型独立存储。生产不提供CPU回退。
- 原生Trainer始终使用完整 ceil(N/8) 总步数；分段只在optimizer更新后保存停止，恢复使用新的output_dir和完整checkpoint。
- `dpo_capacity` 必须另冻最长对优先的至多24项计划，可重复已接纳对；正式 `dpo` 不接受该计划或容量checkpoint。容量更新不混入正式一轮。
- DPO使用独立 `dpo-env`，不可原地替换SFT/generation环境。安装与版本身份已在CPU检查；Linux/CUDA实际安装待Colab实测。
- 实例输出默认 `durability_verified=false`。S1沿用export/recover/ack与stop-ready，汇总全阶段21600秒/12CU预算。

完整命令、失败历史、退出码、实际依赖与数值索引保存在私有目录。没有编辑冻结共享接口或SFT核心的缺口；没有新聊天、sub-agent、真实模型/正式数据加载、GPU分配或Colab作业。

真实Qwen前向、正式偏好编码、CUDA容量/恢复、正式DPO全部NOT_RUN。下一步由S1回读交R1，通过后结合真实Q1清单冻结容量计划。
