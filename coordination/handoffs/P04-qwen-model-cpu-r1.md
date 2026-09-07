# E1 交接：P04-QWEN-MODEL-CPU-r1

**READY_FOR_REVIEW。** 仅交付 CPU 实现与证据，实际模型/框架/LoRA/adapter/训练/推理运行均 NOT_RUN。

- code_base：`a2b595c39d84f4e3ba32ee5893f3fff8c9202f4d`；完整授权：`427e5e8fb49a4719afd5e09b53c2d012c52e7e80`；同轮构建支持：`97ca7091c239f5fbfbdbde2db401eb72532bb38a`。
- 分支：`codex/p04-qwen-model-cpu-r1`；源码提交：`207c24c486a562760c51b8de3193c3e78028ba6d`，直接以 code_base 为父。最终完整候选为包含本交接的最终提交，由普通推送的原生交接及私有 seal 提供完整 SHA；不将源码 checkpoint 当作已完成候选。
- 契约：`plan-v0.1 / coordination.v1 / toolalign.contracts.v1`；ADR-0027；原14授权和2补充均保留，未合并变化中的其他包。
- 新增范围：`src/toolalign/model_io/qwen_model.py`、`tests/model_io/test_qwen_model.py`、S0 原字节 `configs/qwen-models.v1.json`、本交接、实验报告及 JSON，共6个新公开文件；617基线文件保持。

120 项最终 CPU 测试通过；源/安装各1轮两模型20文件hash及622 header通过，0 tensor值解码。实际sdist、direct wheel、从sdist重建wheel和新默认target均完成，65包文件逐字绑定；非源码cwd纯导入、4拒绝场景及固定文件验证均来自target。全库Ruff、契约与源码阶段620路径公开扫描通过，完整文档检查和最终seal另附原生交接。原失败/旧FAIL/PASS保留，未修改协调状态、main、旧代码或依赖。

接口包括固定文件验证、当前真实租约检查、延迟`load_qwen_model`、冻结/固定LoRA装配与参数内容身份、仅A/B的严格adapter重载。参数读取使用原dtype位表示、每次宿主复制≤1MiB；serialized311与预期runtime310/112分开。模拟测试均MOCK_ONLY，不证明真实运行对象或容量；调用方持续持原租约至所有模型引用释放，错误后对象进入FAILED。

详细证据和限制见 [报告](../../reports/experiments/P04_QWEN_MODEL_CPU.md)／[JSON](../../reports/experiments/P04_QWEN_MODEL_CPU.json)。源码SHA `e9ecf4ad145682da239c422e3e3e3f156b4d7c203758f330317c6f4456d10e1a`，测试SHA `e432807eec158a46859914b22e8805fe835c2427f7845e076ba924fbbb64ed00`；固定配置SHA `b8a5e48bc2b93064c511ba796dabf55024f65df97fe0db39c43366b7bc877145`。归档/安装证明 `f5c4dbd69e3332f30dae50ad372d114ee70a88822a083818be95028dc22e46ce`；source/installed固定文件证明 `21512c5f0787b23a86c1f76c43f9c561717c0fb4869b6e53f9c4d90619d94ffd` / `c4416f988c27a205dfc0279d0e293d8200a2893b9f1d5eddc2d8613277a319a2`。

19:16 UTC保全4,376当前路径，原498公开Git/快照、1,209旧scope、39链接、3旧refs与根identity保持；旧公开checkout位置按原Git及快照登记。新scope/真实任务身份、原argv/UTC/exit/stdout/stderr、源码epoch、归档/target实物与全部失败仅存本机，绝对路径不写公开交接。

两条本轮辅助非零保留：unused test import、测试期望错误前缀不符。S0另在旧共享pytest临时根发现fixture缺失，归属/替代证据由S0核查；本轮前四次pytest未传basetemp，不宣称该外部旧目录保全通过。后续任何pytest用新独占、非`.toolalign-local`祖先的`--basetemp`，不重跑既有成功或恢复/清理旧目录。

S0核验完整候选和原生终态后，按精确新范围派R1。独立审查、最终CI/main及所有真实模型路径仍待完成；源/安装原文件验证额度各已用1/1，E1不再追加。metadata不是执行授权，正式P04训练/评测/服务许可不因本次CPU交付改变。
