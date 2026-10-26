# P05 G4 真实候选与偏好处置 Q1 审核 r1

2026-10-26，独立审核者 Q1 AI。结论：**NO_ELIGIBLE_PAIRS；80 条正式候选均未成功，偏好池和审核样本均为 0，误标率不定义，DPO 质量门 BLOCKED。** 分母、输入身份与零对提取处置核对一致；这不构成偏好质量 PASS。按原 ordinal 升序，首个已返回动作仍符合合法策略的超时候选为 **ordinal 8（第 9 条），seed 50**，可供 S1 在运行时修订验收后选择一次独立诊断。

授权提交 `3890349baeb7f262230873bd0f52b4d05deeca4e`，实际生成源码固定为 PR28 主干 `6e2f1d28a8e5163ef29515da5cdf3a2c432ec7cc`；范围见[本轮任务](../../coordination/tasks/P05_G4_PREFERENCE_Q1_R1.md)。依据[冻结协议](../../coordination/tasks/P05_G4_PROTOCOL.md)核对[真实生成报告](../S1_P05_G4_GENERATION_R1.md)与原始回收材料。

## 固定分母、身份与提取

S1 输入索引绑定的 42 份文件全部核对 SHA256 和大小。新 tasks、authoring、manifest、summary、group audit 与 Q1 r2 的私有受检包逐字节一致，复用 `50440298a909a509d4cf86185e58c1daa11c1c5d` 的语义、来源和分组结论；20 题仍为同一 train 连通组，原 r1 REQUEST_CHANGES 历史保留。未重做未变化的语料语义审核。

固定清单为 20 题 × 4 候选，seed 42–121；任务文件顺序、candidate ID、采样参数、选中 1.7B step743 checkpoint/adapter、模型 revision、tokenizer、模板和 registry 身份全部一致。执行记录中的 85 份源码文件与执行提交及本地受检文件一致。

完整候选文件前 12 行与 pilot 逐字节相同。完整 manifest 的 80 组 started/terminal 元数据，均与从记录重建的 started 内容及实际 terminal 行的 hash/大小对应；pilot 的 12 组同时保持原 hash。后 68 条使用续段 run ID，清单无缺失、重复或替换。全部 **158 次实际 ModelInput** 均从任务及此前 assistant/tool 事件重建一致；**101 个完整返回动作**的原始文本、解析动作和输入 hash 一致。202 条子进程记录均已回收。仅 23/80 条轨迹的 token 计数完整，其余未返回 token 不按 0 计。

| 正式终态原因 | 条数 |
|---|---:|
| timed_out | 61 |
| invalid_arguments | 12 |
| unadvertised_tool | 5 |
| no_records | 2 |
| success / missing / interrupted / unknown | 0 / 0 / 0 / 0 |

80 条均没有完整成功轨迹，也没有 finalized 终态，不能提供 chosen。对原始记录重新运行现有 CPU 提取器，preferences、lineage、逐候选 dispositions 和 summary 与冻结产物逐项一致：0 对、80 个 `nonsemantic_termination`、缺失终态 0。该标签只表示不满足正式偏好提取条件，不能解释为 80 条此前都没有语义错误。

原空池、分层配额及 seed42 sample 未改变。按当前 `apply_review` 格式交付 `sample_hash`、`reviewer="Q1 AI"`、空 judgments；实际应用结果为 `original_review_denominator=0`、`error_rate=null`、`quality_pass=false`、`dpo_quality_gate=BLOCKED`、`training_preferences=[]`、`training_authorized=false`。本轮没有逐对语义可审，不能写为 0% 误标或将失败轨迹补成成功。

## 首个可区分运行时问题的候选

只审查定位首个候选所需的 ordinal 0–8 前缀；判据为至少一个完整返回动作、所有返回动作仍合法、实际 observation 与至少一条合法剩余策略一致，最终因超时未完成。未返回答案保持 unknown。

| ordinal，从 0 起算 | 判定依据 |
|---|---|
| 0–3 | 提示明确禁止工具；完整首动作已调用工具，虽最终超时也不符合诊断判据。 |
| 4、6、7 | 首次调用合法；只允许一次调用后再次调用，并遗漏必需参数，终态为 invalid_arguments。 |
| 5 | 第二个返回动作重复已经完成的唯一允许调用；终态超时不能消除这个 extra_call。 |
| **8** | 两个返回动作及两次成功 observation 均符合合法策略，第二次决策前已取得首次 observation；第三次请求提交后无返回动作。 |

ordinal 8 的两次调用分别查询版本文档、转换其中的超时数值。转换参数取自第一次实际 observation，数值的整数/浮点表示等价；调用位于不同决策，完整第二次输入确实含第一次结果。第三次输入包含两次结果，合法策略的工具步骤已完成，仍需模型返回合法 final。冷加载记录为 19.125 秒；首次 observation 在 23.437 秒，第二次在 27.687 秒，第三次生成请求在 **27.688 秒**提交，**30.198 秒**记录超时终态。不能写成“第三次请求前超时”，也不能预测未返回答案会正确。

私有 `diagnostic-candidate-0008.json` 保留完整真实 candidate、三次输入、轨迹、任务及 authoring；`diagnostic-selection.json` 保留前 9 条判断。源位置为完整 candidates.jsonl 第 9 行：

- terminal 行 SHA256：`6738ac922ab2ab0c0a51bc8261afc40145cf854fd434ec727d41125df44716d0`。
- candidate canonical hash：`656e5baa52e1a9672224feeb928915252743462524049efe9544ea942d038636`。
- trace canonical hash：`296e22a813f9a40a93ef0f724969678ed8f8d091f348f03a0000f9a676158ca9`。

建议下一项验证由 S1 在批次文件验证复用的 CPU 修订及 R1 审查通过后，以独立 run ID、相同输入、seed 和原轨迹预算诊断此候选，观察第三次请求能否完成以及返回动作是否为合法 final。若动作返回但语义错误，说明释放运行时间仍不足以解决该任务。诊断结果单列，原 80 条、零对和失败记录保持；本审核未授权或执行新运行。

## 监督覆盖与加载归因

正式批次 79 条完整首动作均为 `tool_calls`，另 1 条未返回完整首动作。无需工具类别的 8 条中为 7 次工具调用、1 次无完整动作；澄清类别 8 条均调用工具，其中 5 条终止于 unadvertised_tool。

原 G3 stage manifest 与此前完整数组审核绑定文件逐字节一致，两个数据文件 hash 也一致。本轮只读计数得到：train **5,938** 条、validation **213** 条的监督目标及 category 全为 `tool_calls`，来源均为 Team-ACE/ToolACE。分别有 180/12 条输入以 tool observation 结尾，目标仍为下一次工具调用。这支持“该监督目标集合没有覆盖最终回答、无需工具和澄清动作”，原验证 CE 衡量的是工具调用目标拟合。它与当前首动作分布一致；单凭这两项不能证明 SFT 造成行为退化，因果判断需要原始模型与 SFT 的同协议比较。

独立 profiler 记录使用不同 run ID 和 `REAL_CUDA_SFT_PHASE_PROFILE_DIAGNOSTIC`，只有 1 次诊断，与正式首个输入及 seed42 一致，未进入正式 80 条或偏好池。插桩冷加载 21.807 秒，first_tokenize 阶段 0.900 秒、model_load 阶段 20.995 秒；其中 `validate_model_files` 累计 12.230 秒、`_hash_file` 累计 11.696 秒、SHA-256 update 自身 11.015 秒。嵌套时间不能相加，profiler 开销使其不能直接分解未插桩的 19.083 秒冷加载中位数。证据支持验证复用的性能修订及独立复测，不支持宣称模型动作选择已改善。

## 实际命令与交付证据

本轮独立核对命令 exit 0，使用既有 Python 3.14.7 环境。`Q1_PRIVATE` 为交付消息中的私有证据目录，`PYTHON` 为该既有解释器，从审核 worktree 根目录运行：

```sh
PYTHONPATH=src "$PYTHON" "$Q1_PRIVATE/audit.py"
```

| 输入或证据 | SHA256 |
|---|---|
| S1 输入索引 | `93c8401199e6a5f8b5dd10c91e81604858a756dbd9a03048559cd6f68263f346` |
| tasks.json 文件 | `b9c6f18995579d8af1a58d137cafe9cc1c9f2f40279d9434aa85e2c7769eb015` |
| 正式 candidates.jsonl | `ea1c3dd168bc7d4edc3591186b2d3e8e6de4d5514b983891eb3f4761e1515dea` |
| 原 sample canonical hash | `73cac9826205cde303c06bede01e93fcd091337e578aed0dcc42716436db0f66` |
| Q1 review-result.json | `11b755ca0a11eb39742aa7f365abba34f0d0a41bfe51f259044a8fbbfe3a978e` |
| Q1 evidence-index.json | `8b3de9181a8f01a314b2e995878586d86ec5eada52eb3749467f504d80505742` |

Q1 索引绑定 55 份输入、审核脚本、逐候选核对、空审核 JSON、诊断选择和命令记录。公开变更仅本报告及[交接](../../coordination/handoffs/P05-g4-preference-q1-r1.md)；未改生产实现、原始材料或共享状态，新增模型调用、轨迹、编码、训练及 GPU 作业均为 0。
