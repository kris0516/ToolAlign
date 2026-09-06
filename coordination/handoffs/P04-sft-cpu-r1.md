# P04-sft-cpu-r1｜T1 CPU准备与上游限制交接

2026-09-06；T1，`gpt-6-astra` / `max`，新分支`work/p04-sft-cpu`。状态为**CPU_PARTIAL_UPSTREAM_BLOCKED，候选待独立R1/S0审查**。

code_base `42eaa50a9519efe96d60b49f07cfbd106b36778c`；授权`e42536dd7c77d90ed33ab5354f288ab0f1c3d6c6`。原P01分支、`9fe3cbe`、原独立审查/失败和私有证据保留。真实独立任务身份沿用并已由S0核验，未创建新任务或sub-agent。已读授权AGENTS/PROTOCOL/STATUS、ADR-0020、P04任务/精确配置、docs03/16和S0 readiness/main证据；契约版本未变。

全部变更限于新增`src/toolalign/training/sft/`、`tests/training/sft/`、`reports/experiments/P04_SFT_CPU_*`、本交接和唯一逐字节配置副本`configs/sft-cpu.v1.json`（SHA `5aad6ff6db68ee4fe9bac0aa6104eaeff17bf948b509bfce3d14e3eac9d9aa29`）。364份基线文件保持。没有改公共data/model_io/P01/P03、依赖/锁/CI、旧测试/报告、契约、正式ADR或看板。

交付内容与证据：

- [报告](../../reports/experiments/P04_SFT_CPU_REPORT.md)：只读四视图、新collator、有限累积计划、validation结构与实际限制。
- [机器索引](../../reports/experiments/P04_SFT_CPU_VALIDATION.json)：14条原命令的UTC/argv/退出码/日志hash及实际Git源码epoch，三归档、安装、13例与两次失败进程记录。
- [上游最小反例](../../reports/experiments/P04_SFT_CPU_UPSTREAM_LIMIT.md)：CPU默认设备下原trainer.py:229在进入训练循环前KeyError。
- [隔离安装检查器](../../reports/experiments/P04_SFT_CPU_PACKAGE.py)、[索引核验器](../../reports/experiments/P04_SFT_CPU_EVIDENCE.py)与[受限TOY监督程序](../../reports/experiments/P04_SFT_CPU_TOY.py)；原验证脚本与vendor保持原字节。

真实执行源码：`96fcbe1f34fc9d2afe1d9faf3935817d37b22d76`完成13例新collator测量；`9e71552c22b4ed5daf4e4a66e24816bd61f53092`完成独立mask数值并触发原生入口阻塞；`eefc142ce159c1564076dff7d3f17156412de699`执行最终CPU回归和三份新归档/安装。最终完整candidate/parent/tree、远端读回及最后公开扫描通过原生回报，不能把后续文档提交标成重新执行。

CPU四组970 passed / 2 HF-only skipped，严格为原919＋新51；原格式60、截止时间2、训练绑定13/110 subtests均实际执行。51单独重复、安装和110 subtests不再相加。Ruff、四契约、公开扫描与默认wheel的8个新增模块实际origin检查通过；三份新归档逐成员/Git/metadata/RECORD保持。安装共10条命令，含3条预期失败拒绝；没有新增环境或依赖下载。

原10条train＋3条协议例仅一遍新native编码，全部数组匹配冻结reference/native；新全量重编码0。13条原创TOY的loss最大误差0，gradient最大误差`4.470348358154297e-08`，右padding及ignored-logits误差0，容差`2e-6`。default_loss的额外padding监督真实重现。两次失败分别为初始DLPack探针解释错误和原生CPU元数据KeyError，完整负结果保留；子进程实际reaped、租约释放、无存活自有PID。

**尚未执行**：MLX train循环及optimizer更新、8+5实际尾周期、native evaluate、最终TOY checkpoint/save-reload/post-tail绑定；正式baseline/SFT/accepted_sft、真实P02优化、预训练模型加载、容量预检、GPU操作及后续阶段。Torch参考和纯计数计划不能代替这些门槛。S0已要求按原授权上游限制分支交付，保留原vendor/CPU设备，不重复入口或实施绕过。

183份旧P01 Git身份、1310份旧私有制品、18份原数据和86份selection/review文件保全；新私有目录预算低于2GiB。两份人工表最近核对仍0 reviewer/0 verdict，实际页面观察0；合法人工后续填写不受影响。没有代签G-DATA/P04人工门，没有费用、公网接口或模型/数据上传。

T1普通推送新分支并结束本轮，等待独立R1/S0处理当前候选和已报告上游限制；不自行合并main或领取正式训练。
