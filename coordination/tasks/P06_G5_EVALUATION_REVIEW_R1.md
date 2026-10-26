# P06 G5｜评测执行器独立技术审核 R1

owner R1；收到S1精确候选及索引后，从指定集成提交建立 `codex/r1-p06-g5-evaluation-r1`。实际读取avoid-overkill，按[后端任务](P06_G5_EVALUATION_CPU.md)及[共同协议](P06_G5_PROTOCOL.md)审核。只授权CPU审查与原创小型数值检查，不加载固定真实模型、安装依赖或运行GPU；既有CPU环境可只读复用。

核对T1实际候选、源码身份、命令/退出码、私有原始证据及报告。沿用未受影响的旧SFT/DPO/G4证据，不重跑全量矩阵。E1工具候选 `6027096` 已经独立R1 `c6c81db` PASS，S1接纳；本轮只核对T1与该精确工具依赖的组合，工具语义旧审核不重复。

重点确认M0确实不载adapter、M1确实使用选中SFT，底座加载共享调整保持旧训练路径；父进程预检与child实际加载对应，无模型输入泄露oracle或测试标签。L1仅消费新的held-out包并按题使用真实subset；recovery off在首次retryable错误终止，默认on和原错误路径保持。

独立检查真实Transformers prefix cache的有效前缀、position/cache长度和输出等价，key包含模型/adapter/tokenizer/template/tenant，错误/取消后不复用。用现有小型随机原创Qwen和预设数值容差，不下载真实权重；至少核对一次有实际计算减少的命中及一次身份/前缀变化的不命中。不能用mock命中代替真实cache，也不将CPU证据称为CUDA性能。

检查固定plan顺序/seed、三种评测mode及独立capacity上界、冷加载纳入30秒、replay同一child最多3请求/90秒。action-only对raw Action独立解析，空/坏输出、deadline、取消及基础设施错误保留各自状态；不得把异常改为合法无需工具。对全计划分母、started禁止重跑、只续未started、外层取消/时限后的owned child回收与最终summary输出预算进行有区分力的CPU复验。复用T1可信的完整矩阵，新增检查针对改变结论或资源安全的关键分支。

核对Colab固定入口和锁仍限制单个自有GPU作业、S1单独运行授权及资源上界；本轮不启动实际远程控制。验证完整输出/原始文本/finish reason/模型身份和计时、token缺失unknown、GPU显存与host RSS区分足以供E1分析消费。若缺少可判定指标，提出具体缺口，不编造结果。

交付 `reports/reviews/P06_G5_EVALUATION_R1.md`、`coordination/handoffs/P06-g5-evaluation-review-r1.md`、精确审核commit及私有evidence-index；明确复用与本轮实测、PASS/REQUEST_CHANGES、稳定issue ID及失败计数建议。仅提交两份审核文档，不代修生产实现或修改共享状态。正式模型效果和GPU性能在本轮仍NOT_RUN。
