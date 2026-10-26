# P06 G5 工具实现独立技术审核 R1

2026-10-26；实际审核者：R1 AI。**PASS；新增 P0/P1/P2 问题均为0。** 固定catalog选择、parent/child源码与subset绑定、旧catalog身份兼容获得支持。独立3项CPU检查通过，4个新owned child全部回收；建议S1接纳本工具CPU包。

| 审核身份 | 精确提交 |
|---|---|
| E1受检候选 | `6027096baf382bb0e50bf3f7463dd11fca0e19d1` |
| S1集成 | `2f6d02e1e662143237cd72def92aad67c144ac99` |
| 本轮授权/审核起点 | `beb26eeebefd6f2a42d678e661e6175d0708f003` |

执行[独立审核任务](../../coordination/tasks/P06_G5_TOOLS_REVIEW_R1.md)，范围为[工具CPU包](../../coordination/tasks/P06_G5_TOOLS_CPU.md)。受检6文件在E1候选、S1集成、授权提交和本地工作树中逐字节一致。T1模型后端不在本轮范围。

## 源码与既有证据

独立回读E1索引绑定的60份私有文件，核对大小、SHA256、实际命令退出码及stdout/stderr，并与S1 intake所绑定的索引一致。E1索引SHA256为 `8ba4a94bb4b5e6aa9f5eecf55e929f99b74359d020d5ae8333274879f508e010`。实际测试回执中的4个生产/测试文件hash与交付一致；JUnit为109 passed，其中新增工具52项、原工具57项，失败/错误/跳过均0。

4组两步执行证据覆盖全部8工具；第二步关联参数确实取自第一步output，8个owned child均exit 0、reaped且临时目录清理完成。本轮复用这些测试及未变的超时、取消、一次性ValidatedCall证据，没有重跑109项矩阵。

- `LocalToolRegistry`仅枚举两个固定catalog，拒绝模块名或callable选择；所选spec、implementation名称和实际源码hash进入manifest。`catalog_id`传入child后重新构造同一subset并核对registry_hash，绑定不符时在执行标记之前拒绝。
- 旧`catalog.py`与授权前版本逐字节相同；默认和显式旧catalog的canonical manifest/spec、6个单工具subset及空subset身份保持。旧完整registry为 `6cf0ff5e0b775068ddd9690e66414eee97725865d520e8df37072bc53d4085b8`；新完整registry为 `66d47196bd207542325c89244a7fbafd2163f14c01e9aeb36e40553e01c7f037`。
- 新工具只查询代码内原创静态资源。发布计划与实际部署、事件窗口与处置规则、构建存在与测试结果、物理空间与租户配额各有明确不同的参数和返回语义；日期、对象、版本及缺记录反例可构造。实现没有读取caller路径、网络或环境。

## 本轮独立CPU检查

沿用已有Python3.14.7/jsonschema4.26.0环境。检查入口如下；私有`independent-command.json`保存实际绝对argv、环境覆盖、源码提交、脚本hash、时间和退出码。

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B .toolalign-local/review-p06-g5-tools-r1/independent_checks.py
```

实际结果为 **3项通过，exit 0**。

| 独立检查 | 实际结果 |
|---|---|
| 旧身份和新源码绑定 | 默认/显式旧catalog的manifest/spec字节、6个单工具subset和空subset全部匹配；新8工具的源码、schema和implementation绑定匹配 |
| advertised subset与有日期的配额 | 未advertise的发布工具在spawn前拒绝；真实读取oryx/scratch的10月21日记录后，物理可用20GiB但6GiB请求超过租户配额；4GiB/74对象恰好达到96GiB/1024对象上限时允许 |
| 错误源码绑定 | 将新工具manifest中的source_hash替换成真实旧catalog源码hash，child返回`rejected/child_binding_mismatch`且未产生执行标记 |

后两项共启动4个真实owned child，均exit 0、reaped且目录清理完成；未导入Torch、Transformers、MLX或PEFT。完整输入、输出、拒绝原因及process records保留在私有证据中。

私有证据入口：`.toolalign-local/review-p06-g5-tools-r1/evidence-index.json`，SHA256为 `19784c74d15f8548bb24fb1be6acf1a0dcd92813ddc209549baef6b375601a85`，绑定69份文件，包括E1原始证据副本、独立回读结果、检查脚本与实际执行回执。

本结论支持工具CPU实现与绑定。四域的真实连通group、最终L1任务语义和隐藏oracle由后续D1/Q1审核；held-out隔离尚未验收，正式模型评测仍NOT_RUN。本轮没有生产修改、依赖安装、模型加载或GPU操作。按[REVIEW_POLICY](../../coordination/REVIEW_POLICY.md)，新增问题0，正式修订失败计数不增加；共享状态由S1维护。
