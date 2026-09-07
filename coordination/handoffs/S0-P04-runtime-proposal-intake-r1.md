# S0｜P04运行方案输入核验

2026-09-07 14:28:40 UTC。task `P04-SFT-RUNTIME-PROPOSAL`，code_base `d3e56f68ebd67cc576d912b6f06636682b4170ab`，authorization `8929cbbef0b24f9a4053adfe778bb4ef76147293`。S0工作分支main；契约plan-v0.1 / coordination.v1 / toolalign.contracts.v1，Action JSON v1保持。仅更新协调/输入接收证据，没有生产变更。

T1实际新分支`codex/p04-sft-runtime-proposal-r1`与精确base、独立任务身份及gpt-6-astra/max核对通过。5,617条当前文件路径、197个旧链接、553份基线和408份原f732 Git/快照保持；18份授权逐字匹配授权提交，10固定输入合计166,598 bytes匹配manifest `eb5f25bd164c1394c0d82350a1f1d0ccc09ddb1306dac3977403b695d7f1ac02`。两份原intake/切分支回执及stdout/stderr绑定通过；原P01/CPU refs不变。

S0接收脚本首次执行PASS，证明SHA `eeaa498ea5a7e481b1bde7def42db9cedc3d2ddda71b4491891663929eb9592f`；脚本SHA `82d3e95e9c7b2daa7c375c1075ae339a3750b0513f6f3802ebcd71524911f099`。原私有失败记录保留，完整方案及最终执行封存仍待交付。公开检查用`python scripts/check_public_content.py`和`git diff --check`；源码及实物hash核验仅stdlib读取。

[只读方案范围](../tasks/P04_SFT_RUNTIME_PROPOSAL.md)继续；分段原生train、累计optimizer step和最终状态验证须写成待实施方案。S0新增数据构建、环境、安装、tokenizer、框架、模型、GPU均0。G-DATA及正式P04仍未授权，不把intake记成训练接口验收。
