# S0｜P04 真实运行方案接收

2026-09-07，**ACCEPTED（只读方案）**。T1 完整候选 `4baa367b4a331addc442e447269605bad85cdbe0` 已交付、远端一致、原生 completed/idle；S0 于 15:16:38 UTC 完成接收核验，以普通 merge `7bf05d1eaa1c346486e03d16ab6e7485d06809b7` 保留原提交纳入 main。方案可作为后续精确实施范围的依据；生产实现、真实容量、baseline/SFT 与 G-DATA 没有因此获准或通过。

基线 `d3e56f68ebd67cc576d912b6f06636682b4170ab`，完整授权 `8929cbbef0b24f9a4053adfe778bb4ef76147293`，`plan-v0.1 / coordination.v1 / toolalign.contracts.v1`。仅新增 [文字方案](experiments/P04_SFT_RUNTIME_PROPOSAL.md)、[结构化对应件](experiments/P04_SFT_RUNTIME_PROPOSAL.json)及 [T1 交接](../coordination/handoffs/P04-sft-runtime-proposal-r1.md)。S0 直接接收本授权范围内的规划材料；没有把这次接收写成独立 R1 技术 PASS。

## 实物与来源核验

- 556 份候选文件逐字对应 Git；553 份基线文件不变，新增仅上述三份。候选直接以 d3 为父，tree `eb26342ad550126d02faf2c5e510e9d5a066b12a`。
- 18 份授权、10 份固定输入／166,598 bytes 与原 S0 副本一致；35 份源码和 80 个行区间逐字、逐 hash 核验，包含四份现有 MLX 文本源码。没有导入框架验证这些引用。
- 原 5,416 条证据路径、197 个链接及 408 份旧 Git 身份保持。旧 checkout 的 18 个内容差异来自已授权切换至 d3，未称为物理字节不变。
- worker final seal `60705a506247b896e7f29c3a0d2c24bdc0ebeb143f024c0bca195af04f055814`，156 文件／6,542,816 bytes；补核 self 与真实收尾 recorder 后为 161 文件／6,788,263 bytes，低于 128MiB。
- 20 条真实命令的 argv、UTC、source head/tree、前后公共 hash、stdout/stderr、原生进程退出码均绑定；19 条在 final seal 内，末条由独立收尾回执 `f67d970b6a4cf008cd37db648e1fdee2b8e2a5acbc79da351efe47945ba65701` 绑定。

接收证明 `a1ba2afc23f88f217eab54242b0b63345ceaaa99ab6bd5ab40705e6844ccbf4e`，核对 5,744 条实际文件路径；私有证明、完整命令和原始输出仅保存在本机。最终文字／JSON／交接 hash 分别为 `a50babe5b96526e98ee8b4472c008d4230356c4b5757c7b19f0cdd0d210356a2`、`bc57cd61092f32eb6de489372fca910da0f4df8a31a62886f24a479a70c7bbc8`、`997923166265806afa305cef3b04d0483bc2a182ec39e9bdfa7ea7d037d72280`。

## 接受的规划内容与限制

| 范围 | 已核对的方案 |
|---|---|
| 新数据消费 | 独立 v3 prepare／CPU 数组导出；原 v1 入口和固定 toy 守卫保留。GPU 消费冻结 Batch，不在 MLX 导入后构造拒绝框架环境的 CPU tokenizer |
| smoke | 1,583 微步分 528／528／520／7；divisor 8／8／8／7，计划 198 更新，完整评分 step 66／132／198 |
| formal | 5,938 微步分 2,000／2,000／1,936／2；divisor 8／8／8／2，计划 743 更新，完整评分 step 250／500／743 |
| 状态与计数 | 每 profile 四次原生 train／四次保存，连续 model／optimizer／RNG；局部 closure、iterator、it 重建。覆盖 1..N，无丢尾；实际更新与同步完成不能由 yielded rank 推定 |
| 保存与验证 | 返回后绑定真实 adapter 文件、实际 optimizer step 与完整 validation；模型模式恢复，重载严格匹配，baseline 和不同运行 scope 分开 |
| wired 设置 | 原生 train 每次调用 setter。复用既有抑制守卫；合成返回 0 不代表观测到原 wired 上限，生成的恢复 setter 也需抑制 |
| 容量候选 | 15 train／8 validation、79 微步／10 更新、一个 GPU child／0 重试／900 秒等仅为 PROPOSED_NOT_AUTHORIZED；具体 ID、数组、配置与预算待 S0 冻结 |

上述更新算术和两份投影完全一致；实际 v3 manifest、模型加载、原生 0.6B 1536／1.7B 2048 容量、BF16 padding 容差、保存重载及生成停止条件的运行证据仍 PENDING／NOT_RUN。模型、LoRA、Adam、编译和诊断阈值仍为后续配置提议，不能把结构化方案当运行授权。实际数据优先等 D1 完整候选、R1 技术、Q1 实际处置／材料与 main 验证，再冻结 CPU 消费包。

## 原始失败与实际检查

T1 两次辅助失败原样保留：引用行区间越界和执行计数字段数量误期望，修正后另有成功回执。探索性查找失败另记。最终公共材料及 helper／来源快照已封存；并非所有中间 JSON 草稿都单独保存，原 stdout 和各时点 hash 不能替代缺失草稿字节。最终 `--require-handoff` 元数据检查实际运行于 d3 加工作树新文档；最终 commit 上的 seal／远端检查不称为重跑全部测试。

S0 接收辅助程序前三次因投影键结构、JS 字符串边界及把源码读取误识别成 recorder 调用而失败；三个原脚本／stderr 保留，仅修正核验程序后第四次通过，未改候选或旧证据。这些不是正式质量修订失败，issue 台账不变。

本次 S0 与 T1 新生产测试、build/install、数据构建、分词、框架、模型、GPU、优化、生成和业务 API 均 0；文档接收按来源、算术、所有权和公开内容检查，未增加无关 pytest。P00–P09 目标继续，费用／公开上传／服务边界保持。

后续准备：2026-09-08，S0只读核对既有两模型的20个文件／原P01身份和9份环境METADATA，[文件绑定](S0_P04_LOCAL_MODEL_INPUTS.md)通过。没有新增编码、框架或模型执行；真实容量/运行配置继续待后续精确授权。
