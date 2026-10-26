# P05 G4｜批次模型文件验证复用 CPU 修订 r2

owner T1；复用既有独立worktree，从S1派发的精确授权commit建立 `codex/t1-p05-g4-model-validation-r2`。先实际读取avoid-overkill和systematic-debugging。目标是消除已测得的重复全文件哈希成本，同时保持实际模型身份、独立child、推理输入及30秒轨迹deadline。

观测：[80条正式轨迹](../../reports/S1_P05_G4_GENERATION_R1.md)冷加载中位数19.083秒；独立一次cProfile诊断的模型文件验证累计12.230秒，其中SHA-256 update自身11.015秒。诊断冷加载21.807秒，包含profiler开销，不能直接当作未插桩运行的分解。现有 `validate_model_files` 已保存每个文件的device/inode/size/mtime_ns/ctime_ns；生成却在每个child重新扫描全部固定文件。无需先引入常驻模型服务。

最小方案：生产批次在首次模型child启动前完整验证固定模型文件一次，取得只在本次进程内传递的已验证元数据；每个child加载前及加载后核对实际路径、固定模型/revision/config、文件集合及未变的stat身份，再复用验证结果。任何文件内容、替换、路径或元数据变化均明确拒绝，不使用过期结果、不静默回退。重启批次或新实例仍重新完整验证；不建立跨运行持久缓存，不以单独外部声明的hash代替实际首次读取。

优先复用 `ModelFiles` / `FileIdentity` 与现有文件安全检查。必要的公开辅助API应只服务这一实际调用链，不添加通用缓存框架。`cuda_sft.engine.load_model`可增加显式、可选的已验证文件参数；SFT/DPO原调用默认仍执行完整验证。保持FP32 adapter/BF16底座、LoRA加载及实参hash、CUDA lease、框架导入顺序、sampling seed和decode代码；父进程的预检只读文件与JSON，不加载模型或导入Torch。

批次计时从预检前开始，全文件验证的真实成本进入segment/分配预算，并在summary单列；child冷加载指标明确说明已在批次预检模型文件，不能把移动后的时间与r1作未说明的同口径比较。预检计时不要加入决定resume batch hash的动态身份，固定模型/执行语义身份仍须绑定。恢复只继续未启动ID的行为不变，原80条终态不得重跑或覆盖。

允许修改 `src/toolalign/model_io/qwen_model.py`、`src/toolalign/model_io/cuda_generation.py`、`src/toolalign/training/cuda_sft/engine.py`、`src/toolalign/training/cuda_generate/` 中必要接口及对应定点测试；新增 `reports/P05_G4_MODEL_VALIDATION_R2.md`、`coordination/handoffs/P05-g4-model-validation-r2.md`。不改固定模型/config/模板/contracts、任务/oracle、DPO实现、依赖锁、Colab控制器或共享状态。与E1的DPO runtime修订保持文件范围分离。

CPU验证使用原创小文件及现有fixture，覆盖首次真实哈希、未变身份复用、原位内容变化/同大小并恢复mtime、inode替换或symlink、错误模型绑定，以及变化在模型加载期间发生时的拒绝。选取能证明实际边界的少量检查；复用未改变的默认SFT和生成接口证据，不下载真实模型、不做Mac推理。允许复用已有专用CPU环境，不改环境。

交付精确commit、实际定点命令/退出码、计时与身份字段说明和私有证据索引。R1独立检查后，S1另行冻结一次小型Colab诊断，比较原完整返回动作与新实际轨迹；本任务不授权GPU、修改任务或生成新正式偏好。文件验证优化不能声称修复动作类型选择或产生DPO质量提升。
