# T1｜G6 CUDA受限服务 CPU r1

2026-10-27，S1派发。起点为派发消息给出的精确S1协议提交，父主干为PR34 `98d642a116da94f2ab2b2aaeb6e931f79fd5cabc`。在自己的既有worktree新建`codex/t1-p07-g6-cuda-service-r1`，保持原提交与私有证据。先实际读avoid-overkill及[总协议](P07_G6_PROTOCOL.md)、[HTTP字段](../../docs/18_RESTRICTED_CUDA_SERVICE.md)。本轮只授权CPU开发，不加载固定模型、不访问/分配GPU。

目标：固定M1服务可显式prepare、保持warm/cache、经loopback接收单决策，并对鉴权、队列、幂等、截止、取消、身份/训练互斥和退出给出可复核行为。你的只读预审已被采纳；以下为正式边界。

## 允许改动

`src/toolalign/service/`、`src/toolalign/inference/`；`src/toolalign/model_io/cuda_generation.py`、`cuda_evaluation.py`中实际需要的prepare与内部lease/cache身份接缝；必要的单一纯结果gate helper及`evaluation/cuda_eval/decision.py`复用点；对应`tests/service/`、`tests/inference/`、受影响现有model_io/decision检查。Colab适配仅由你修改`scripts/colab/support.py`固定service命令/预算分支及其现有测试；如真实入口调用还需一处现有controller接缝，先给S1具体差异和理由。

公开交付仅新增`reports/P07_G6_CUDA_SERVICE_CPU_R1.md`、`coordination/handoffs/P07-g6-cuda-service-cpu-r1.md`；私有命令、日志、输入/输出与索引放`.toolalign-local/p07-g6-cuda-service-r1/`。不修改client、共享HTTP文档、contracts/依赖、registry、oracle/题集、训练数学、BOARD/PROJECT_STATUS/DECISIONS。已有harness与DecisionSession的默认3次/90秒保持，不扩展成通用服务平台。

## 实现要求

使用标准库与既有OwnedProcess/GPULease/CUDA解码/cache；新增服务child循环和短HTTP控制面，串行调度器独占child生命周期。backend在父进程构造，再进入owned child；prepare提取当前tokenizer初始化与load路径，无假请求/隐含warmup。真实child持GPU lease，并使用明确service身份。已加载/仍存活/当前worker epoch共同决定ready，重载不得复用旧ready文件。

启动配置`toolalign.service-run.v1`、`authorized_by=S1`、`run_kind=serving`，固定CLI为`python -m toolalign.service serve --run-config ...`。复用当前批次文件验证模式和精确模型/adapter身份；启动配置由S1决定路径、token映射、loopback端口、cache开关和有限预算，客户端无路径/采样覆盖。配置必须支持S1冻结的900秒、256MiB及至多12次实际生成smoke上限；64条记录是软件硬上限。

请求遵循共享HTTP精确字段，principal由auth映射经IPC进入cache key；同key回读先于容量拒绝，不刷新deadline。`GET /v1/tool-decisions`按Idempotency-Key只读查询，不存在时不创建，供客户端在丢失响应和已超时后安全查回/取消。仅一个cache entry，失败/active取消/超时清理；入队前拒绝不破坏当前健康请求。输入tools只接受`local-devops.v1`原样子集，允许空集；不执行任何工具。

30秒是接受后含排队/重载/生成的决策截止；清理尾段另计。服务总截止前5秒停止接受/生成并开始清理，外层900秒硬限收尾。queued取消/过期不启动模型或杀其他请求；active先stopping，回收确认后终态；未确认停止接受并保留真实状态。输出预算覆盖最终summary/状态/原始请求，不能补写后越界。保留所有accepted/started/terminal和worker回收记录，缺失token/phase为null。服务崩溃不自动续跑旧run。

## 必要验证与交付

CPU用真实loopback和真实owned child核对：loaded-ready顺序；未经认证/越权拒绝；同key重读与冲突；队列/累计容量；排队截止与取消不误杀active；active取消/超时回收后才终态；重载/cache/principal身份；GPU锁冲突；输出预算；service controller合法/非法run。以原创CPU工作负载验证边界，不装载固定Qwen；保持旧评测受影响检查通过。

给出源码和测试精确提交、关键命令/退出码/失败保留、实际child回收证据、公开内容检查及私有证据索引。模型/真正CUDA服务为NOT_RUN。自测不代替R1审核；S1接纳后与E1组合并交R1，不自行合并main或触发GPU。
