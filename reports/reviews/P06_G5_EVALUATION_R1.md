# P06 G5 评测执行器独立技术审核 R1

2026-10-27（Asia/Shanghai）；实际审核者：R1 AI。**PASS；新增 P0/P1/P2 问题均为0。** M0/M1加载分支、真实prefix cache、完整失败分母和有界接续获得CPU证据支持。新增6项独立检查全部通过，8个新owned child全部回收。建议S1接纳本CPU实现，继续冻结L1任务、BFCL adapter/scorer和开发replay输入。

| 审核身份 | 精确提交 |
|---|---|
| T1实现 | `d674bdda3166836e8f41d60b763f23374aaa1e8d` |
| T1最终交付 | `60c52f8f189ea49b9c13231e7987974ad48a8ac5` |
| S1集成及本轮审核起点 | `e580eb663b5658e611ce30a1bf7d1232ccba3917` |
| 已接纳工具依赖 | `6027096baf382bb0e50bf3f7463dd11fca0e19d1` |
| 工具独立R1审核 | `c6c81db24feda5986436facd66cc0757bb44e269`，PASS |

范围为[独立审核任务](../../coordination/tasks/P06_G5_EVALUATION_REVIEW_R1.md)、[后端CPU任务](../../coordination/tasks/P06_G5_EVALUATION_CPU.md)及[共同协议](../../coordination/tasks/P06_G5_PROTOCOL.md)。本轮仅新增此报告和交接，不修改生产实现或共享状态。

## 源码及复用证据

T1候选共17个文件。实现提交与最终交付之间仅两份说明文档变化；最终交付、S1集成和受检工作树中的17文件逐字节一致。工具依赖的6文件与已接纳E1候选一致，不重审其语义。

回读并复制T1索引中的28份私有文件，逐一核对字节数和SHA256，与S1 intake绑定一致。T1索引SHA256为 `896698eb296b2d35fbeb478df73cc580e323710e2755dcec61fe3cbcdcbd277d`。接入工具前的测试快照包含189文件；与当前源码的差异仅为E1已接纳的`tools/executor.py`和`tools/registry.py`。交付源码快照及两份文档变更记录也已核对。

复用T1实际 **231 passed、1 skipped，exit 0** 的定点记录；跳过项为既有DPO控制器中需要未安装`pip`的参数检查。该矩阵覆盖M0/M1分支、旧G4 decode及默认loader、harness、recovery开关、三种评测模式、独立capacity上界和Colab控制。没有重跑未受影响的旧SFT/DPO/G4矩阵。

随后针对真实`heldout-devops.v1`的 **1项组合检查通过，exit 0**：新reader、真实subset、owned model child和bound tool child衔接，两条recovery-on轨迹成功，off在首次transient后终止。回读的8个process records均reaped且目录清理完成；输入spec篡改反例被拒绝。该输入是原创组件fixture，最终L1任务仍由D1/Q1独立冻结。

## 实现判定

| 边界 | 核对结果 |
|---|---|
| M0/M1及共享加载 | M0调用`load_model(with_adapter=False)`，不读选中checkpoint、不挂载或恢复adapter，身份为`adapter_hash=null`；M1保留step743完整checkpoint及实际adapter参数hash校验。旧训练调用默认`with_adapter=True`。CUDA设备、文件及加载分支的CPU测试明确使用MOCK_ONLY边界，未据此声称完成固定模型加载 |
| 预检、冷加载与锁 | 父进程导入/构造不加载模型框架；生产入口完整文件预检与child加载前后stat复核对应。child使用共同仓库的真实`GPULease`，原descriptor、PID和owner核验保持。30秒请求/轨迹预算包含冷加载；父预检单列并进入段预算 |
| L1与恢复开关 | reader要求新schema、catalog和test/ood_test一致性，按题核对真实subset spec。模型仅收到ModelInput，oracle和fault schedule留在host。默认on保持旧行为；off在首次retryable错误/工具超时后终止，不改变不可重试错误及全局deadline路径 |
| Cache | 单进程单项`DynamicCache`，完整模型/adapter/tokenizer/template/tenant身份进入key。仅保留上一prompt的前n−1个tokens，裁去生成状态；命中时重算剩余后缀。错key、token前缀不符、跨进程或失败生命周期不可继续复用。off/on使用相同采样、插桩和CUDA同步位置 |
| Plan及资源上界 | M0/M1按输入序号交错且同题seed相同；A1复用原seed，replay交错off/on。L1≤104轨迹、action-only≤120请求；replay≤8序列、每序列3请求/90秒；capacity≤2请求/60秒。Colab入口固定且要求S1授权，段/分配上界及输出上界保留，跨段总账由S1管理 |
| 原始输出和接续 | action-only独立解析raw Action，不信任backend修复值，不执行工具。started先于后端构造写入，任何started单元不重跑；replay保留请求journal并关闭失败child。全计划均导出，未启动、超时、取消、解析失败、基础设施错误和中断保持各自状态 |
| E1消费与计量 | 保留raw文本、finish reason、完整ModelOutput、实际身份、请求配置和process records。known token合计与完整性分离，缺失为unknown；TTFT/prefill/decode、冷加载、队列、工具时间、GPU显存及host RSS各有字段和范围。官方分数与严格门控由后续E1消费，当前scorer状态为NOT_RUN |

## 独立CPU实测

只读复用已有Python3.12.14、Torch2.8.0、Transformers4.57.6、PEFT0.18.1、NumPy2.2.6、pytest9.0.2环境。私有`independent-tests-r1.command.json`保存实际绝对argv、cwd、环境覆盖、退出码和耗时。入口为：

```sh
PYTHONPATH=src "$CPU_PYTHON" -m pytest -q .toolalign-local/review-p06-g5-evaluation-r1/test_independent.py --basetemp .toolalign-local/review-p06-g5-evaluation-r1/pytest-r1 -o addopts=
```

`CPU_PYTHON`指该已有环境解释器；实际结果 **6 passed，exit 0**，没有失败或跳过。

| 独立检查 | 实际结果 |
|---|---|
| 原创两层Qwen，裸模型与真实PEFT各1项 | 5,744/6,640参数，初始化seed271828、采样seed47；17-token旧prompt扩展为20 tokens，实际命中16、首轮forward仅4 tokens，无cache首轮为20。默认decode、插桩off与hot的68个输出tokens相同；模板身份变化及前缀token变化均miss，重算20 tokens |
| 混合终态与started接续，1项 | 6项完整分母保持为2 completed、2 parse_failure、1 interrupted、1 infrastructure_error；仅unit3/4/5启动，unit0/1终态文件字节不变。backend将空原文伪装成合法parsed_action仍被独立raw gate判为失败；5个child回收 |
| 外层取消及deadline，各1项 | 取消在真实child已进入generate后触发；另一项由段deadline停止阻塞child。分别保留1 cancelled或1 timed_out及3 not_started，token完整性false、缺失unknown；2个child均停止、回收并清理sandbox |
| 恢复后的输出预算，1项 | 已完成unit保持原终态；以1 MiB预算接续时不再启动新项，保留1 completed与3 not_started。包含最终summary的实际文件总量11,333 bytes，低于1,048,576 bytes；原child已回收 |

数值容差在执行前固定为`atol=2e-6, rtol=2e-5`。逐步末位置logits的off对默认decode最大绝对差均为0；hot最大绝对差分别为 `5.960464477539063e-08` 与 `4.470348358154297e-08`。热请求发布后的cache长度为19，符合20-token prompt保留n−1的约定。这证明原创CPU数值与计算复用，CUDA耗时和模型效果需要后续实测。

私有证据入口：`.toolalign-local/review-p06-g5-evaluation-r1/evidence-index.json`，SHA256 `37b0ffba3384481f2c03695b30e26ef2340a75a6492ed66e01b5797d2c844787`，绑定96份文件，包括T1原始证据副本、源码对应、独立脚本/日志、完整journals和结果。

本轮没有固定权重加载、下载、依赖安装、Colab或GPU操作；正式模型评测、官方BFCL和M2均NOT_RUN。按[REVIEW_POLICY](../../coordination/REVIEW_POLICY.md)，新增问题0，稳定issue列表为空，正式修订失败计数增量0。S1可接纳CPU包；最终输入、Q1语义/分组与E1官方评分接口通过后，再冻结单独GPU运行授权。
