# P02-format-fix-r3｜修复交接

2026-09-06，D1，gpt-6-astra / max；`work/p02-data`。状态：**READY_FOR_REVIEW**；待 S0 正式派发独立 R1 复审。

授权 `c6c02a5af084afe92c6e9f05d9d1c51392e805d0`；原候选 `7bada2e451d43dae4b3ed532d5efa310fc8e6a57`；代码提交 `b4dc1cf5c7d8c551506a7015bca2400573e16857`，父为该原候选。同轮同步授权 `6272ad512b947b9cf14c5f7201b7807f7f188e13`；安全证据提交 `7b8ef310db214845ef5ac1fabfef1e37e9e05ab0` 后普通 merge 唯一公开原 review `2942e568eae91d0292ad9691af133bbd8c33dd02`，形成最终被测完整 `6c82d29ddaade349d3e2a15f50d35214dbc7bf8d`（父为 7b8ef31 / 2942e56）。最终交接提交只增加本文件和本轮报告/证据，完整 SHA 由原生消息交给 S0。12 份原 review/FAIL 保持；R1 本地原 f708 与公开 2942 的 SHA 不同，f708 不在祖先。未接后续 main/P01。原 F1 等级保持 P2，正式原审查 P0=0/P1=0/P2=1、FAIL。

只修改 `src/toolalign/model_io/offline.py`，新增 `tests/model_io/test_snapshot.py`；既有 tests、格式/序列/资源与原数据、人审、manifest、依赖、P03、状态均保持。真实 HF 从三份已核验 buffer 的临时只读快照加载，原目录额外文件不参与；成功与异常均清理。此修复绑定来源更新期间的实际加载状态，不承诺同用户 OS 任意篡改隔离。

- 原反例实际复现：7bada2e reference exit 1，声明相同而 `!` 由 `[0]` 变 `[30]`；native exit 0。修复后同探针两 engine exit 0，真实 backend 与原正常基线一致，loader/返回值/identity/hash 均未 mock。
- 新 reference pytest 13 passed；合并后组合旧 CPU/真实 native/旧独立测试 675 passed / 2 skipped，原 R1 结构/统计 60 passed / 0 skipped 分组执行；两组共 735 passed / 2 skipped。reference 13 passed / 0 skipped 在合并候选实际执行，包含两个 HF 专属 cleanup。七个来源额外文件与三个预存篡改场景在两 engine 各执行并通过；场景重叠与安装重复不累加成独立测试分母。
- 同 12 个原 fixture 在两 engine、两个固定模型身份下重新核验完整 P/C/IDs/sequence/EOS/masks，全部实际字段和角色/身份与原 v1 相同；每 engine 24 个身份行，独立 fixture 为 12。新全量重跑为 0，原 8,228 行 native/source/time/hash 未重标；原 R1 7bada 上的一遍全量 reference 公开结果与 S0 证明已只读核对，rows hash 和全部 all/by_split 汇总与保留 native 相同；仍保留原源码、fsspec 2025.3.0 环境与时间，不重跑或重标。
- 当前 sdist 88 成员、默认/显式重建 wheel 各 44 成员，39 份包源码/资源逐字节匹配；10 条默认 CPU 隔离安装/接口命令通过，无可选 tokenizer/模型依赖。默认 wheel 实际来自 sdist；源码直接 wheel 为 NOT_RUN。实际构建和纯接口安装绑定 b4dc1cf，合并后当前 Git 载荷不变。另在 6c82d29 将默认 wheel 新装 target，两个真实 engine 原反例均通过，每次七个 ToolAlign 导入均来自该 target，39源码/资源 hash 匹配、源码导入0；安装重复不增加独立场景。
- 原 234 个公共文件、新合入12份原R1文件、620 个旧 v1 私有文件、37 组旧命令及日志保持；原两套各 18 制品与 100 来源/114 决策人审及未填写副本 hash 保持。未代签 kris 人审。

原缺陷 FAIL 和开发新 pytest 首轮 7 failed / 6 passed 均保留。开发失败来自测试临时路径别名和 vocab 匹配条件，修正测试后 13 passed；生产修复 byte hash 始终为 `f1354c349708c09e82661fbde3d7b9b96df16a5f9634b28097b66973bbe4ddf3`。初次 after 测试时 HEAD 为 7bada2e、工作树已有此字节，证据按实际记录，不伪写历史运行 commit。之后初次组合和归档测试绑定 b4dc1cf，合并后分组回归/HF测试/真实默认wheel反例绑定6c82d29。新增一次组合收集因两个原test_independent模块同名而exit2，原日志与启动器保留；仅私有启动器改为两组调用后全部通过，原测试未改。

详见 [修复与验证报告](../../reports/data/P02_FORMAT_FIX_R3_VERIFICATION.md)和[全部命令/来源/失败证据索引](../../reports/data/P02_FORMAT_FIX_R3_EVIDENCE.json)。三个真实归档、原始结果、完整日志和命令元数据只存本机；定位信息和最终候选/普通推送/干净状态由原生交接附上。S0 首次封存探针当时是未提交 R1 源码快照，后续正式2942中的三份对应源码逐字节相同；两个阶段的身份和时间分别保留。

只使用既有 CPU 环境，没有新 tokenizer 环境、联网下载、模型/GPU、费用、上传、训练或部署。D1 自测及候选 CI 不替代独立 R1、新格式验收、G-DATA 或 P04。普通推送精确候选后结束本轮，等待 S0 后续授权。
