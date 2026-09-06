# P04 原生固定 toy：S0 中间核验

日期：2026-09-07；授权 `de86568d73ee77bbf92b6f749a39a9ab38955836`，代码基线 `50867c0be43d110df6c3620c94022fcfdaf779b5`，配置 SHA-256 `fb06634d00b0565a60dc22ea829ac509732b3b6429b9bbbc2ff6207c974850cb`。

状态：T1 的原生任务仍在进行。本报告确认两次历史源码运行的实际数值、checkpoint 字节及一个监督器缺陷的定点修复；最终安装版、完整候选、独立 R1、CI/main 尚不在本报告的验收结论内。P04 正式训练仍未授权，P00–P09 整体目标未完成。

## 原输入与独立参考

原 CPU 两次运行使用的原创输入文件保持 SHA-256 `df4b87001074e9fab6c3a330cf516dca17cfab1bb7505d97025ceeb31d3b5b47`，原生成器保持 `3872ed4187b0754b9baa32525a6aa3b157e33c0d7ceb7b9d1336f34df4536ed0`。其 13 个固定 rank 中，rank 1 与 13 的数值载荷相同，共 12 种不同载荷；没有去重、替换或重新编码。模型仍为 8×8 的 64 个 float32 参数、词表 8、padding 桶 16、EOS 7、SGD 0.07、seed 42。

S0 用 Python 标准库重新推导原数组、CE 和全部梯度，逐个 64 参数做标量中心差分，最大差 `4.3414327688395815e-11`。解析参考给出 8+5 两段的独立期望值，仅用于数值对照，不是一次新的框架训练；参考证明 SHA-256 `125f4a16fce6b9b3da37d1f49b1027e163b3d4aa2602f4a5e7b9d2186ebc9bba`。

## 实际源码数值与状态

两次实际 GPU 运行均发生于源码 `534445bb8eecd600b65e90e541cd30601b4fd07c`，消费身份 hash 为 `6d6a54d533428b8bf97f72a12242a46851b7a86d736584c371a010dcb56c53d0`。完整、权威的消费身份逐文件保存在私有 preregistration；下列核验以实际 Git 字节和原日志为准。

S0 在 18:57:18.420552–18:57:18.872257 UTC 实际检查 162 个原件/快照路径，以及 56 个消费源码的 Git blob。原数值产物与冻结副本逐字节相同；逐例 CE、完整 64 梯度、有效分母、shift/EOS、右 padding 和被忽略位置 logits 均与原输入及独立解析值一致，绝对容差为 2e-6。最大 CE 差 `1.904749407088957e-7`，最大完整梯度差 `2.3736388549133736e-8`。原 default_loss 反例实际将有效 token 从 2 增至 3，CE 从 `2.074565887451172` 改为 `2.0883114337921143`，未被隐藏。

| 实际状态 | optimizer step / 已处理微步 | 实际 divisor | 参数与 Torch 最大差 | 实际 token 加权 validation CE |
|---|---:|---:|---:|---:|
| 分段第一状态 | 1 / 8 | 8 | 1.862645149230957e-9 | 2.066978758031672 |
| 分段最终状态 | 2 / 13 | 5 | 1.862645149230957e-9 | 2.0616965131326155 |

两个实际 safetensors 均按文件头、offset、F32 dtype、8×8 shape 和完整 256 字节参数独立解析；不能仅靠文件名或更新计数通过。第一 checkpoint SHA-256 为 `06f9f5dcc8dbc6e399313eaac83b4506d90521f24793644b29c0c15fe43df58b`，最终为 `17906c78b9689f4e75768eb2bbe23ce5853db2a66833e295b10b2fa9436eb132`。对应参数内容 hash 分别为 `5ba7425d55a387f46565841126cc5aae207d4deae3219a9913a36be512738cff` 和 `0c4907f87df8c5d58efd31e3ba40a14fa6a5a28d3342c4394905ae6ad091a2dd`。

实际训练顺序为 1–13，各一次；两段保留同一 model/optimizer/RNG 对象。每个实际保存状态完整遍历同一 13 例，分母均为 44 个有效监督 token。score 的 selection、validation 身份、参数内容、checkpoint 文件、step/microsteps 相互绑定；实际保存重载参数和 score 完全一致；将第一 checkpoint 绑定到最终 model 的调用实际拒绝。确定性规则选中第二状态。这些相同 toy 样例仅核对状态记账，不构成泛化或模型质量测量。

独立的原生单段运行保持 13 微步、accumulation=8，实际只更新一次，其 checkpoint 字节等于分段第一状态；与完整两更新 Torch 状态最大参数差 `0.013687163591384888`，遗失尾部 5 微步。该进程成功记录的是 EXPECTED_NEGATIVE，不是尾批处理正确。

两次实际 GPU 子进程 wall 分别为 `5.215603958815336` 和 `2.9626315420027822` 秒；峰值 RSS 分别为 `399605760` 和 `387514368` 字节。两次同步采样的 MLX peak 均为 `5864` 字节。实际租约先于框架导入，MLX default/stream 为 GPU，Torch 为 CPU、intra/inter-op 各 2 线程；原生 train/evaluate/compile、trainer/datasets 原件保持，wired-limit setter 请求仅被既有上下文抑制并恢复。两个进程实际 exit 0、wait/reap、PID 不存在与共享锁释放记录完整，S0 再次只读确认原 PID 已不存在。toy 用时与内存不外推真实模型。

原分段 stderr 含一个 resource_tracker 的 semaphore shutdown warning，原始日志保留。S0 只对该原确切名称执行未带创建标志的只读 sem_open，返回 ENOENT，确认核验时该名称不存在；这不是全局 semaphore/进程泄漏审计，也不将原 warning 改写为空日志。

本次 S0 数值/字节核验证明 SHA-256：`563a3e83a6682f33a2b869833d15aaca4a03310241cb3e26fa0b82fcfffcd9d1`。私有审计脚本 SHA-256：`2d9e81c6119710ce3168ae969194d4ca8eaad15e3091f8de18df19cd3234f649`；原命令 exit 0，完整 stdout SHA-256 `2173b005d633b49fe1eb1c5e11882337b38390bc76b754ad949175b3a2e7afbf`，stderr 为空。S0 未导入 MLX/Torch/NumPy，未增加 framework run。

## 监督器失败终态修复

S0 在原 `534445b` 发现：monitor 的磁盘超限异常能够触发真实 terminate/wait，但最后构建结果时再次执行磁盘统计而抛错，导致 supervision.json 缺失、失败模式不能重新登记。S0 以一个真实自有 CPU sleeper 和注入的磁盘异常复现；原证明 `eab2cfd764d6487092203748dad75c1d7a4f161d7eef6fb40196156265c5ae70` 保留。首次 S0 复现辅助脚本缺少 sys.modules 的装配失败也保留，未计作有效反例。

T1 的修复提交为 `fae3d608b6edc3f5dc941dfb3395757ee3db2ef3`；native_toy.py SHA-256 `f4ce51fecad6bc914f806a9cd53c631166651212503ae5e376a32eb01a0aaedd`。它将 cleanup 与最后的诊断分开，逐项捕获诊断错误，保存真实 exit/PID 状态，并保证 child 最后退出路径不被诊断写入异常跳过。原成功源码数值仍属于 `534445b`，没有冒充在修复后重跑。

S0 于 18:49:12.679581–18:49:12.810167 UTC 在冻结修复源码上运行原同一 CPU 故障路径，并增加最后 consumer_identity 同时失败场景。两个真实自有 sleeper 均被修复后的 public supervise 终止回收，ps 确认 PID 不存在，终态包含原 monitor 错误与后续 diagnostic_errors，fixture 的失败模式可重新登记；没有新框架调用、GPU 租约或真实 2 GiB 写入。定点回归 exit 0、证明 SHA-256 `d387826e624d5c44724481eacbbab9de24d32ffe8a280e572d0a95836fa6d314`，脚本 SHA-256 `976abf3eac8fd37061f9a6f8c1792e69c47ef0d3e6307b92f0a2d69df1779dd5`。此处通过仅关闭已报告的具体缺陷，完整候选仍须独立 R1。

## 原失败及剩余验收

T1 首次源码 parent 预检因私有 CPU guard fixture 的 symlink 退出，发生在 ledger/child/framework 启动之前；修订只计链接自身字节，不跟随目标，输入/输出链接拒绝规则保持。T1 首次完整 CPU 组因 basetemp 位于被扫描的私有祖先和遗漏 tokenizer 环境变量，实际为 881 passed/2 failed/48 skipped；这是原装配失败，不计入最终通过数。最终正确环境 CPU 组、归档、安装和源码 epoch 应由完整交接逐项核验；不得合并不同轮次来隐藏失败。

T1 的 framework 额度仍由 ADR-0021 管理，R1/S0 新框架执行须单独明确范围。原 CPU 上游 KeyError/0 MLX 更新、原 R1 CPU PASS 与已合并 PR10 保持。实际页面观察、kris 语义/token-mask 人审、真实模型容量、baseline、SFT/DPO、正式评测与部署均不因上述 toy 结果完成。
