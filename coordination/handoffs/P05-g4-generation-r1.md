# P05-g4-generation-r1 交接

T1 已完成 [CUDA 候选生成 CPU 包](../../reports/P05_G4_GENERATION_CPU.md)，待 S1 回读与 R1 独立技术审核。授权 `6d5df60591dda6c5e63b8d8c8b8f45bbb828d022`；同时落实 `6deeb0c9b32b6f8dcfd0149b6972ba1f68b0dd43` 的 interrupted 规则和 `8b84a524c55bdb31edc9425814ce8eb2575e9f48` 的逐候选独立 faults 规则。

交付范围：

- `src/toolalign/model_io/cuda_generation.py`：owned-child lazy load、固定 G3 SFT 身份、逐键 adapter 校验、完整模板输入及 CUDA-only 解码。
- `src/toolalign/training/cuda_generate/`：严格任务/配置验证、固定完整计划、CPU plan/validate、生产 generate、原子 started/terminal 日志和保留失败的恢复。
- `src/toolalign/evaluation/harness.py`：可选采样、实际 decision_inputs、冷加载统计回收；原预算和默认 greedy 保持。
- `scripts/colab/{control,remote,support}.py`：增加固定 generation schema/module 分派与 max_trajectories 预算，复用原回收/中止路径。
- 四个对应测试文件、本报告与交接。未改 contracts、模板/descriptor、SFT 生产代码、依赖、工具/oracle、P02 数据或共享状态。

验证：受影响范围 170 passed / 2 skipped（既有 pip parser 检查）；最后的统计读取回收修补另有 18 passed。Ruff、4 文件冻结契约、812 路径公开内容扫描及 diff check 均 exit 0。全部命令、退出码、耗时、失败记录、源码绑定与私有产物入口位于本 worktree 的 `.toolalign-local/p05-g4-generation-r1/handoff-index.json`，由最终回复提供可点击绝对路径。模型前向、真实 SFT 候选和 L4 性能 NOT_RUN。

给 D1/S1 的接口要点：

- 全顺序是任务文件顺序 × candidate-0..3，seed=42+全局 ordinal；每次 decision 重置到候选 seed。必须先冻结完整 candidate_plan。
- max_trajectories 是累计计划前缀上界，包含 pilot 和恢复项。恢复必须使用新输出目录与相同 batch identity；已有终态不变，started 无确认终态为 interrupted，不能用重跑成功覆盖。
- candidates.jsonl 同时提供顶层 decision_inputs 和 asdict(harness_result) 内的相同副本；保留实际 call_id、observation、原始文本和采样参数。没有返回的超时请求可多出最后一项 input；不会补造 decision。
- status 的普通值为 success/failure/unknown/not_scored；interrupted 或 infrastructure_error 可含 null harness_result，必须保留候选分母并排除偏好。格式、长度、超时等细节以真实 harness_result 为准。
- generation run config 使用独立 schema，不设置 max_optimizer_steps/persistent_dir；字段和三条 CLI 命令详见报告。
- S1 在实际执行时汇总 G4 全阶段分配时长、CU 和设备总占用；本代码的 Torch 峰值及记录耗时不替代这些成本。

没有需要编辑冻结公共接口或 cuda_sft 生产文件的缺口。本包未创建独立聊天或 sub-agent，未占用 GPU，也未发消息给其他 worker。
