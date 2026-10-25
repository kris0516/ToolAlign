# 16｜Colab 训练工作流与显存预算

2026-10-26。当前目标是把 ToolAlign 的已审数据/损失契约移植到 CUDA；本页是接续规格，尚无 ToolAlign CUDA 训练结果。

## 可复用的基础

另一研究项目已使用官方 `google-colab-cli 0.7.4`、ADC、OpenSSH 和 tmux，验证 A100 80GB 同实例断线后后台继续、工程 checkpoint 新进程恢复；另有 L4 上真实 3B LoRA 诊断。工程 fixture 为连续 24 步与 12+12 步恢复对照，参数和后续 RNG 一致。实例回收后在新实例恢复的整链尚未验证。

本机具体脚本、SSH alias 与证据位置在私有 `LOCAL_HANDOFF.md` 和本地 `colab-remote-training` skill 中；公开文档不放账号、会话 ID 或凭据。已有 A100 初始化脚本硬性检查 80GB，不能原样用于 L4；旧环境也未锁定 TRL。

官方 [Colab CLI](https://github.com/googlecolab/google-colab-cli)提供命名会话、SSH、执行和文件传输。先用现有包装执行 `sessions`/`status`；显式创建新会话才使用 `new -s RUN_ID --gpu L4`，需要时选择 `A100`。SSH 代理模式可能在会话不存在时自动申请资源，因此保留已部署包装的“先确认存在”逻辑，替换旧项目固定会话名。新 Supervisor 首次操作前读当前版本 `--help`，不用猜测参数。

按当前 [Colab FAQ](https://research.google.com/colaboratory/faq.html)，SSH 等额外限制针对免费且无正计算单位余额的运行时；付费且有余额可移除该组限制，仍受通用规则和动态回收约束。复用既有账户，不能据此购买/充值。不要用 keepalive 绕过平台限制。

## 一次作业的具体流程

1. 固定 Git commit、模型 revision、数据/序列版本、LoRA、优化器、精度、batch、长度、步数和输出。先写预算，再申请一个命名 GPU 实例；不改其他项目会话或共用其运行目录。
2. 读取 `nvidia-smi` 的型号/实际显存、Python/CUDA/驱动。环境、模型缓存、工作数据位于实例本地盘；单独锁定 PyTorch/Transformers/PEFT/TRL。现有 Mac `uv.lock` 保持 CPU/历史用途。
3. 在 `/content/toolalign` 部署精确源码，只传已批准、运行所需的数据。准备和训练是不同入口；安装或 import 不能自动开始训练。把可恢复的输出放独立 ToolAlign 持久目录，不写另一项目的结果。
4. 用 tmux 启动作业，记录 run ID、PID、即时日志和退出码。客户端断开后先查看已有进程、日志、checkpoint，再恢复；网络报错不能触发第二份同名训练。
5. checkpoint 保存模型/adapter、optimizer、scheduler、步数、数据游标与 RNG，以及配置和依赖身份。adapter 权重单独不足以恢复训练。先在实例本地完成原子写入，再复制到持久盘并读回；Drive 挂载不是数据已经持久化的证明。
6. 完成后回收日志、checkpoint、指标与最终配置，确认持久化，再对本任务实例 `stop -s RUN_ID`；读回活动会话。安装、空闲、重试和归档也计入 GPU 时间。断 SSH 或关浏览器不释放资源。

`tmux` 只跨客户端断线存活；平台回收会结束进程并丢失本地盘。新实例必须重建锁定环境，再恢复完整 checkpoint。该路径需实际验证，不能从同实例恢复推定通过。CLI 自带的 `colab skill` 可查操作细节；本项目不沿用其中无条件换 GPU/重启/重新提交的建议。

## 显存估算

以下是规划估算，**不是测量结果或容量承诺**。单位为 GiB；显卡标称 GB 与实际可分配量不同。假设 BF16 冻结底座、Q/V 28 层 rank 8、FP32 adapter/梯度/AdamW 两个状态、microbatch 1、SDPA、gradient checkpointing、`use_cache=False`。是否保持这些数值方案须由新 CUDA 配置明确。

参数来自仓库 [固定模型配置](../configs/qwen-models.v1.json)，使用去除重复 tied head 后的独立参数量：

| 项目 | Qwen3-0.6B | Qwen3-1.7B |
|---|---:|---:|
| 冻结参数 | 596,049,920 | 1,720,574,976 |
| BF16 基础权重：参数 × 2 bytes | 1.11 GiB | 3.20 GiB |
| Q/V rank-8 可训练参数 | 1,146,880 | 1,605,632 |
| adapter+grad+AdamW：参数 × 16 bytes | 0.017 GiB | 0.024 GiB |
| 既有最大序列长度 | 1536 | 2048 |
| 一份完整 BF16 logits，词表 151,936 | 0.435 GiB | 0.580 GiB |

FP32 logits 上述大小翻倍；反向和临时张量可能再增加占用。激活、CUDA workspace、分配器碎片和验证/保存峰值另计。梯度累积 8 不会使单微批峰值自动缩小。

粗略分配区间：0.6B SFT **4–8 GiB**；1.7B SFT **6–12 GiB**；1.7B DPO 若固定 reference 可正确预计算并释放，**8–16 GiB**；独立 reference 驻留且成对计算时先按 **12–22 GiB** 预留。这些区间用于选首次硬件，不是从参数公式推得的精确峰值。未经 checkpointing/高效注意力、使用更长序列或更大微批时重新估算。

因此 SFT 优先 L4。DPO 必须计入 chosen/rejected 两路和真实 reference；固定参考可按锁定版 [TRL DPO 文档](https://huggingface.co/docs/trl/en/dpo_trainer)预计算 reference log-probabilities，再释放对应驻留状态。参考应是选定 SFT 起点；直接关闭 SFT adapter 可能变成原始底座，改变目标函数。预计算需绑定相同参考、tokenizer、样本、截断和 log-prob 规则，验证等价后才使用。

旧 MLX 有效 scale 2 映射到标准 PEFT 为 `lora_alpha/r=16/8`，`use_rslora=False`；不是把 alpha 直接设为 2。实现依据见 [PEFT LoRA 参数](https://huggingface.co/docs/peft/en/package_reference/lora)。

## 最小容量验证与 A100 选择

在实现/数据就绪后，SFT 与 DPO 各对其实际最重配置做一轮有界探针：2–3 个完整 optimizer step，包含首次优化器状态分配、最长冻结序列、真实 reference 路径、一次验证、保存/恢复再一步。DPO 要等偏好与 SFT reference 准备好，不能现在用空壳算通过。

记录 `max_memory_allocated`、`max_memory_reserved`、`nvidia-smi` 总占用、CPU 内存、step time 和有限 loss；Torch 计数和设备总占用不相加。测试首步与稳定步，避免只测“加载成功”。

目标是保留至少约 20% 实际显存余量。若预估已超过约 80% 的实际总显存，或 L4 探针 OOM/余量不足，选择 A100；不为塞入 L4 静默改变长度、样本或目标函数。切换硬件保持协议和预算身份。`--gpu A100` 不保证 80GB，`--high-mem` 是主机内存选项；申请后必须读实际硬件。
