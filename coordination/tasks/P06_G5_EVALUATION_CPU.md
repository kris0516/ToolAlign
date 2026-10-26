# P06 G5｜CUDA评测后端与有界执行 CPU 首包

owner T1；在既有独立worktree从S1派发的精确提交建立 `codex/t1-p06-g5-evaluation-r1`。先实际读取avoid-overkill；实验按experiment-readiness。执行[共同协议](P06_G5_PROTOCOL.md)，本包只授权CPU开发与已有环境中的定点检查，没有真实模型加载、模型下载、GPU、远端运行或新依赖安装授权。

交付M0/M1真正分离的懒加载评测后端。M0不挂载或恢复adapter；M1复用已选SFT验证及实际权重hash。复用固定decode kernel与owned model child，父进程不加载Torch或模型。只为共享真实底座加载所需最小调整 `cuda_sft.engine.load_model`，保持原SFT/DPO默认行为与原G4入口不变；不要复制两套固定文件验证或改变training config。延续一次父预检、child加载前后stat核对与全部成本计入。

新增 `model_io/cuda_evaluation.py`、必要的 `model_io/prefix_cache.py` 与 `evaluation/cuda_eval/` 有界执行入口。支持三种明确模式：L1走现有LocalHarness和host oracle；action-only对固定ModelInput做一次生成并保存原始Action JSON，供后续BFCL官方scorer；replay对同一owned child中的固定最多3个ModelInput做前缀缓存对照。输入/输出格式与可复用的one-decision调用在报告中完整说明，便于后续E1 adapter直接产出和消费，不引入可执行模块名、任意handler或通用RPC框架。

L1任务包采用新schema `toolalign.evaluation-tasks.v1`、purpose=`heldout-model-evaluation`、catalog=`heldout-devops.v1`。每项保持G4 entry中的task_id/family_id/group_id/category/example/oracle_task/faults，新增tool_names；example与OracleTask split必须test或ood_test且一致。每项构造对应subset registry，核对example工具与其真实spec一致。E1同时为LocalToolRegistry新增固定catalog选择；在该包未集成时用原创CPU fixture验证接口，不伪造新工具实际PASS。不能放松旧train-only reader或复用G4任务当heldout。

执行run新schema `toolalign.cuda-evaluation-run.v1`、run_kind=`evaluation`，保留S1单独授权、精确source/input/model/lock、max_wall_seconds和max_output_bytes；条件、mode、固定plan及seed形成稳定batch身份。复用原子started/terminal和owned进程回收行为；任何started的模型调用不能自动重试，未启动项才可接续。summary包括完整计划分母、终态原因、未启动项、实际身份/资源、prefill/首token/decode和加载指标。必要时只抽出已有公共小函数，不复制整套控制器。Colab support新增固定白名单入口并验证G5上限14,400秒、最大正式plan224条，replay与容量探针独立mode/计数；所有final summary计入输出预算。

LocalHarness增加显式recovery_enabled（默认True保持现行为）。False遇首次retryable工具错误/超时即终止并记录reason；两方仍相同3决策/2工具轮/30秒预算。不要改变不可重试错误、oracle、Action或trace契约。

prefix cache只支持本owned child中的单条精确token前缀复用，容量不超过2048，不持久化。key绑定model/adapter/tokenizer/template/租户身份；错key、非匹配前缀、被取消或失败的状态不可命中。用当前Transformers的真实cache实现，核对固定版本API；不要用计时开关或mock命中当实现。保持每次采样seed和HFGenerationConfig完全一致；原decode_once默认路径保持。计时不能因off/on采用不同同步/插桩而不可比，明确冷/热范围；对未来G6可复用，但此处不建HTTP服务。

定点CPU证据用已有小型随机原创Qwen fixture检查无cache/冷cache/热cache输出token或逐步logits在预设数值容差内一致、确实少算匹配prefix，以及模型/adapter/template/token/租户改变时不复用。使用真实当前库，不下载权重。覆盖M0无adapter与M1身份、recovery on/off的真实scripted执行、完整失败分母、started恢复不重跑、action-only不执行工具或泄露oracle、预算与实际owned child回收。只测受影响分支；现有CPU环境可只读复用，不改共享环境。

允许修改上述新模块、`model_io/cuda_generation.py`必要共享decode扩展、`training/cuda_sft/engine.py`、`evaluation/harness.py`、`scripts/colab/`固定入口及对应测试。E1独占tools/，本包不改工具目录、冻结contracts/模板、依赖锁、数据与共享状态。公开报告 `reports/P06_G5_EVALUATION_CPU_R1.md`，交接 `coordination/handoffs/P06-g5-evaluation-cpu-r1.md`；交付精确commit、实际命令/退出码、私有证据索引及接口说明。R1独立审核和S1集成后才可获得GPU实测身份。
