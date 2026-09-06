# P02-format-fix-r3｜修复交接

2026-09-06，D1，gpt-6-astra / max；`work/p02-data`。状态：**IN_PROGRESS**；已收到同轮正式审查同步授权，当前先保存合并前阶段证据，最终验证与交接在本轮继续。

授权 `c6c02a5af084afe92c6e9f05d9d1c51392e805d0`；原候选 `7bada2e451d43dae4b3ed532d5efa310fc8e6a57`；代码提交 `b4dc1cf5c7d8c551506a7015bca2400573e16857`，父为该原候选。最终交接提交只增加本文件和 `P02_FORMAT_FIX_R3` 报告/证据，完整 SHA 由本轮原生消息交给 S0。未自行 merge 后续 main/P01 或改写原 review/FAIL；最终来源/包载荷与 b4dc1cf 的字节绑定见私有交接校验。

只修改 `src/toolalign/model_io/offline.py`，新增 `tests/model_io/test_snapshot.py`；既有 tests、格式/序列/资源与原数据、人审、manifest、依赖、P03、状态均保持。真实 HF 从三份已核验 buffer 的临时只读快照加载，原目录额外文件不参与；成功与异常均清理。此修复绑定来源更新期间的实际加载状态，不承诺同用户 OS 任意篡改隔离。

- 原反例实际复现：7bada2e reference exit 1，声明相同而 `!` 由 `[0]` 变 `[30]`；native exit 0。修复后同探针两 engine exit 0，真实 backend 与原正常基线一致，loader/返回值/identity/hash 均未 mock。
- 新 reference pytest 13 passed；组合旧 CPU/真实 native/旧独立测试 675 passed / 2 skipped，两个 HF 专属 cleanup skip 已在 reference 单列执行。七个来源额外文件与三个预存篡改场景在两 engine 各执行并通过；场景重叠与安装重复不累加成独立测试分母。
- 同 12 个原 fixture 在两 engine、两个固定模型身份下重新核验完整 P/C/IDs/sequence/EOS/masks，全部实际字段和角色/身份与原 v1 相同；每 engine 24 个身份行，独立 fixture 为 12。新全量重跑为 0，原 8,228 行 native/source/time/hash 未重标；S0 已送达原 R1 正式 review，历史全量结果将只读登记，不重跑或重标。
- 当前 sdist 88 成员、默认/显式重建 wheel 各 44 成员，39 份包源码/资源逐字节匹配；10 条默认 CPU 隔离安装/接口命令通过，无可选 tokenizer/模型依赖。默认 wheel 实际来自 sdist；源码直接 wheel 为 NOT_RUN。
- 原 234 个公共文件、620 个旧 v1 私有文件、37 组旧命令及日志保持；原两套各 18 制品与 100 来源/114 决策人审及未填写副本 hash 保持。未代签 kris 人审。

原缺陷 FAIL 和开发新 pytest 首轮 7 failed / 6 passed 均保留。开发失败来自测试临时路径别名和 vocab 匹配条件，修正测试后 13 passed；生产修复 byte hash 始终为 `f1354c349708c09e82661fbde3d7b9b96df16a5f9634b28097b66973bbe4ddf3`。初次 after 测试时 HEAD 为 7bada2e、工作树已有此字节，证据按实际记录，不伪写历史运行 commit。之后组合和归档测试绑定 b4dc1cf。

详见 [修复与验证报告](../../reports/data/P02_FORMAT_FIX_R3_VERIFICATION.md)和[全部命令/来源/失败证据索引](../../reports/data/P02_FORMAT_FIX_R3_EVIDENCE.json)。三个真实归档、原始结果、完整日志和命令元数据只存本机；定位信息和最终候选/普通推送/干净状态由原生交接附上。S0 封存探针是未提交 R1 源码快照，不能冒充正式 R1 独立交接。

只使用既有 CPU 环境，没有新 tokenizer 环境、联网下载、模型/GPU、费用、上传、训练或部署。D1 自测及候选 CI 不替代独立 R1、新格式验收、G-DATA 或 P04。普通推送精确候选后结束本轮，等待 S0 后续授权。
