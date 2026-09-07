# P04-sft-data-v3-cpu-r1 交接

**READY_FOR_REVIEW_CPU。** T1 已交付固定 v3 的四个不可变 view、13 例原审阅数组的转换/有限导出/回读和最小有效 CPU 反例。源码与默认安装实物消费都通过；本候选独立 R1 **NOT_RUN**，不自行验收 main 或正式模型训练。

任务 `P04-SFT-DATA-V3-CPU`；branch `codex/p04-sft-data-v3-cpu-r1`；base `48be4352bbad53ced5af84186edac036dd0ff2ca`；原授权 `0fa77e228021091e357505a0e81a5d3ba0777928`；契约 `plan-v0.1 / coordination.v1 / toolalign.contracts.v1` 与角色保留 Action JSON v1。完整候选 SHA 和远端回执在本交接单落盘后的原生消息及最终私有 seal 中给出，避免将文件自身包含的 Git commit 伪造为自引用。

生产 checkpoint `bfdf2a256065d5396e6f7a4860fd7c7506f5c278`；S0 重试授权 `8c8aff8300bfa564db7d47be79e6c3f764360a8b`，grant SHA `0dcef6488eeec3f246560dabd7590a2239fd1238b97073cf5758fb7b8e549bbe`。最终源码 `7ed5d26dfe2658abc6a1681fedc6f9858fdbedda3446de554ea924879ebc7671`，测试 `0ac26360ef75ac0061a77157895d12063b8e5089e2d47acf3ec77c78ea6a448a`；配置逐字节复制，SHA `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1`。全部源码/config/tests 冻结后才执行成功的固定 source/installed 消费，其后只补三份文档。

影响文件仅六份：`src/toolalign/training/sft/data_v3.py`、`tests/training/test_sft_data_v3.py`、`configs/sft-data-v3.v1.json`、两份 `reports/experiments/P04_SFT_DATA_V3_CPU` 报告和本交接单。原 data/config/collator/plan/CLI/model_io、v1/v2/v3 生产器、toy/runtime 守卫、构建/锁/契约与全部 S0 协调文件保持当前 base 原字节。

详细行为、已执行命令、真实来源时点和保留失败见 [实验报告](../../reports/experiments/P04_SFT_DATA_V3_CPU.md) 与 [结构化结果](../../reports/experiments/P04_SFT_DATA_V3_CPU.json)。报告 MD SHA `e9f69b6a39dd53491ef8513a1dfd27bba33913bfe8d8ca115b0360d06571d14c`，JSON SHA `0650cefdf8230c35e6ca8dc4f9aaeb82a89a07f4990314ff819b28ed6d4372ef`。

| 交接项 | 已取得结果 |
|---|---|
| 输入与批准 | 609 固定成员；精确 config、v3 祖先与 R1/Q1/S0 批准；历史 pending 原字节保留 |
| 四个 view | smoke 1583/194；formal 5938/213；有效全集 7419/230；原行与 v1/v2/v3 ranks 稳定绑定 |
| 固定材料 | 13 唯一例 / 26 原 engine 记录；10 train + 3 protocol-only；原 11+2 编码出处和 Q1 身份保持 |
| 数组与输出 | 7 未 padding / 6 padded 数组及所有 token_texts 逐类型、逐位置一致；source/installed 容器与 manifest 字节相同 |
| 测试 | 新增最终 135 passed；常规较早轮 758 passed/3 failed，原三例换新临时根后 3 passed；计数不叠加 |
| 打包与安装 | 当前 sdist、direct wheel、sdist rebuilt wheel、默认 target 65 包文件一致；原失败时点归档/target 保留 |
| 执行次数 | 源码/安装 prepare 各 2（包含原失败）；完整转换/导出/回读各 1；全量 build、新编码、实际更新均 0 |
| 余额 | 固定消费、build、install 均 0；不新增生产运行 |

原失败完整保留：`unit-r1` 的测试路径错误；`cpu-r3` 三个旧测试依赖公开临时根；`fixed-source-r1` 的历史 external-root 绑定错误；`fixed-installed-r1` 的混合 Q1 seal 类型错误。源码首次失败无 terminal profile counter，只保留真实 traceback/源码推断边界；安装首次失败实际计数已落盘。S0 固定追加许可下的新 source/installed 两次均 PASS，所有旧失败、request、reservation、helper 和实物不覆盖、不改名为通过。

稳定接收锚点：source `fa9ec294f5eeef84a15f0a435180c4b528f098d181ba3e93c84fbf6c63b8e0fe`，installed `4237a21dba30e9d3c4cd643d41beffb1ca0259ded1e4918e2ce52ab6da826593`，完整输出比较 `ca8c3008959d6a9b4478775280d677023c80885ad080de723ae3ca93ccc168d1`，当前归档/安装核对 `89cff9aa8459be610025f76706ed38e7a4da4132bb275314695fcd39a800a5e7`，原证据保全 `e6ef5436c6aef3262298aca8d4c07506e79a15b43d0ed5fbe8d17c717a8a4eb6`。最终原生消息将附完整 candidate、最终 seal 路径/hash、scope/预算与实际 commit/push/远端回执；最终 seal 绑定原始日志和私有完整材料，不提交原始数据或私有路径。

后续由 S0 核对完整 candidate 后派独立 R1，新增反例并复核四 view、完整数组、consumer、失败与额度。R1 与主干验证尚未发生，不给自己签正式 PASS。真实 trainer、浏览器实显、0.6B/1536 和 1.7B/2048 容量、正式 SFT/DPO/评测/API 服务继续 **NOT_RUN**；本包没有新模型、GPU、费用或上传授权。普通推送、原生交接后本轮结束。
