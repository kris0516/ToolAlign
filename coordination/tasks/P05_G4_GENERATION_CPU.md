# P05 G4｜真实 CUDA 候选生成 CPU 实现

状态：READY；owner T1；base `1267d1a33dfb08bfd9800b80ea97315730748952`。工作分支 `codex/t1-p05-g4-generation-r1`，复用T1现有隔离worktree。S1提交本任务后的精确授权commit由派发消息给出。

目标：实现[共享协议](P05_G4_PROTOCOL.md)中的CUDA ModelBackend、批次生成CLI及有界Colab调用入口，供S1之后实际生成512条以内train候选；本包只做CPU开发验证，不加载真实模型、不分配GPU。

允许修改：新增 `src/toolalign/model_io/cuda_generation.py`、`src/toolalign/training/cuda_generate/`；`src/toolalign/evaluation/harness.py`中必要的可选采样参数和实际decision_inputs记录；`scripts/colab/{control,remote,support}.py`中白名单generation入口；对应 `tests/model_io/`、`tests/evaluation/harness/`、`tests/training/`、`tests/colab/` 的定点测试；本包报告 `reports/P05_G4_GENERATION_CPU.md` 和交接 `coordination/handoffs/P05-g4-generation-r1.md`。生产实现可复用现有cuda_sft只读API，确需编辑时先给S1具体接口原因。

禁止修改：contracts、model_io模板/descriptor、P02数据、工具catalog/oracle、依赖锁、共享状态、D1任务/偏好实现、既有冻结run授权。不得建立sub-agent或新聊天，不占用他人worktree；沿用gpt-6-astra/max。

要求：

- 后端只接收ModelInput/GenerationConfig。按固定qwen-models和已审SFT协议验证模型及选中checkpoint；BF16底座、FP32 Q/V LoRA，逐键加载state adapter并核对hash/scaling。保持GPU lease、CUDA-only和本地文件加载，无网络模型下载或CPU推理回退。
- 复用已冻结model_io渲染/tokenizer；完整schema/历史、不偷偷截断。eval/no_grad、实际token计数、raw text不修复，截止/长度失败如实保留。采样seed/config逐条固定；无工具答案或oracle进入生成输入。
- LocalHarness默认行为和原测试不变；仅显式传入采样时生效，3/2/256/30秒预算不开放覆盖。增加decision_inputs以保存实际ModelInput并绑定hash；默认调用方兼容。
- 首版模型在已有owned child内lazy load，同轨迹复用，终止后回收；记录冷加载成本。先交付可测路径，不预建常驻服务。若30秒冷加载在真实pilot不足，由S1根据测量另定最小修订。
- 输入/输出严格按共享协议。进度按task/candidate固定ID保存，恢复只续未完成项；不因断线重复已完成候选，不把失败隐去。批次有明确轨迹数、墙钟、输出上限及输入/源码/模型hash。
- Colab控制器仅增加明确白名单generation kind/module，SFT原路径兼容；生成配置使用真实max_trajectories边界，不能填虚假的max_optimizer_steps。检查现有输出回收和中止路径也适用，不引入任意shell入口。

CPU验收覆盖真实接口行为：隐藏oracle不流入模型、可选采样与默认greedy、首分歧输入hash记录、输入溢出/length/deadline、子进程回收、固定ID恢复不重复、控制器入口白名单/预算和SFT回归。测试命令与实际退出码入报告；模型前向、L4性能与真实SFT候选标NOT_RUN。避免镜像实现的过量mock。

交付精确commit、diff范围、定点测试和私有证据索引；由S1回读后交R1独立审查。无需直接发消息给其他worker；可在最终回复列出具体接口缺口，S1用wait_threads收取。
