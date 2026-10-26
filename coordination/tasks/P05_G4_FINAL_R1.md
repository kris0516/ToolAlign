# P05 G4｜运行时诊断与最终处置技术复核

S1，2026-10-26。独立R1 AI，既有独立对话与隔离worktree，gpt-6-astra / max；禁止sub-agent。按当前主干PR29和本任务授权提交建立新分支。CPU只读复核，不分配GPU、不安装依赖、不调用模型、不改生产源码和共享状态。

## 固定输入与问题

实际诊断执行主干`3250f1b83ecbaccea535d74232d6c3f28ffe4df7`，已通过最终头双Python CI并验证文件树。详见[S1报告](../../reports/S1_P05_G4_GENERATION_R1.md)。私有输入索引由S1派发消息给出精确路径与hash，包含23份回收产物、run/auth/script绑定、S1回读、原ordinal 8及完整80条、此前独立接纳和资源结束记录。旧报告与原FAIL保持。

1. 独立核对一次诊断的source/config/model/checkpoint/adapter/dependency、80条原分母与单列身份；验证只执行ordinal 8/seed50一次。原三次输入、前两次raw/parsed动作、token数和observations的对应关系须由原始文件复算。
2. 核对父进程一次完整验证、child实际加载身份、30秒轨迹和90秒段、3/2决策工具预算、3个进程回收、23文件恢复/ACK、设备与Torch峰值、失败与资源账。7.219秒child冷加载排除12.307秒预检，不能声称单请求整体加速或已测批量吞吐。
3. 复用已接纳的DPO SUM/mask/reference/CPU恢复及输出预算r2、文件验证CPU审核，不重跑未受影响矩阵。本轮按风险做必要CPU证据核对，记录实际命令、stdout/stderr、输入hash与新增检查，不能把复用证据记作新跑。
4. 审查S1的G4有据降级建议：有效池0，真实DPO CUDA容量/恢复/训练与M2 checkpoint均NOT_RUN；不能据此声称DPO负效果或SFT造成退化。判断该处置是否完整呈现缺失与允许G5只比较已存在M0/M1；若不支持，指出具体缺失和最小有区分力动作，不要求编造chosen或耗尽剩余预算。

## 交付

只修改`reports/reviews/P05_G4_FINAL_R1.md`及`coordination/handoffs/P05-g4-final-review-r1.md`，私有证据放`.toolalign-local/review-p05-g4-final-r1/`。提交精确commit、verdict、问题ID及计数建议、文件hash索引。不得自行更改App goal、发布状态、旧审核或当前BOARD/PROJECT_STATUS/DECISIONS；最终消息交付，S1读取。
