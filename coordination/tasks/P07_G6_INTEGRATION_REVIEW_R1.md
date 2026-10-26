# R1｜G6服务/客户端集成 CPU独立审查 r1

S1于2026-10-27正式派发。实现集成候选为`fa908839859b758ab2444845f9a2ad2c1eae6c57`；审核任务提交只增加本说明与状态。T1原提交`185d857e94c4187b8167515bf9cdadba248960b0`、E1原提交`59b9c482e0faf93b1fbd5836db21933a6d7197a1`，S1已逐项核对交付与私有索引。只读技术审核，真实审核者R1 AI；不得修改生产实现、共享状态或原始证据，不进行固定模型推理/GPU访问。

以S1派发的集成commit为唯一候选。先核对T1/E1各自精确提交、相关source/test/config身份、命令/结果和必要原始失败，再按改动风险选择独立检查。复用未改变的CUDA数值、mask/reference和旧评测矩阵，不能用既有模型运行替代G6服务事实。

范围：docs/18共享HTTP、服务run配置和CLI、prepare/持久owned child/GPULease、单entry principal缓存、控制器白名单与预算、Mac原文/工具桥接、五类原创scripted入口、公开包与文档。S1允许新私有审查脚本，但不让reviewer修实现后自签。

同时只读检查S1提供的私有G6运行辅助：guarded_tunnel.py复用既有会话存在/归属检查，限制loopback与时长；stop-service.py用记录PID、精确CLI和pidfd向自有服务发送SIGTERM；bootstrap/download/monitor沿用已运行G5路径。它们尚未远端执行，本轮不得连接或分配GPU；实际成功只能由后续smoke与终验支持。配置/输入冻结脚本待CPU实现和主干通过后完成，不把草案当运行证据。

至少一条真实新负向请求和一条真实CPU loopback端到端组合；在新建干净CPU依赖环境执行用户入口，不只检查源码。具体命令在候选CLI实际确定后记录。证据应覆盖：

- loaded-ready绑定当前child和实际prepare；一active/两pending/64记录和配置attempt cap；源/模型/adapter/lock身份及训练互斥；没有隐含warmup生成。
- auth决定principal；跨principal查询/取消404；同key同payload只读复用、不同payload409；容量满仍可回读。GET按key只读查回不存在时不创建，客户端过本地截止后不会POST新建。
- queue/deadline与重载共用原始截止；queued取消不误杀active；active取消/超时在真实child回收后才终态；未确认回收明确unknown，且停止接受。
- SIGINT/SIGTERM走有界停服/回收/summary；旧评测默认次数/预算不变；正常leader退出不留下常驻child。进程和锁证据必须来自实际owned CPU进程，不能只mock close返回值。
- cache key含实际model/adapter/tokenizer/template/principal；不匹配、失败、取消、重启后的失效有证据；只有一个entry，没有每principal多模型。CUDA性能仍NOT_RUN。
- Mac独立parse原文并核对ModelIdentity、request/hash、advertised原样schema、参数、call_id，拒绝未授权调用；返回JSON或自称ValidatedCall不成为执行授权。真实registry/executor只执行固定read_only工具。
- token/phase缺失为null；completed只指一次Action建议，scripted成功与模型/任务成功分开。输出预算包含最终summary和全部状态，不靠写完后忽略越界。
- stdout/日志/产物无真实token；公开包包含必要新模块并排除私有数据/权重；原创示例按文档从精确Git checkout取得，现有sdist白名单不含examples/service，不以未授权打包变更为通过条件。新增CLI help和错误配置在CPU基础环境可运行。

不要求对作者每项检查再跑一次；独立组合/负向/信号/干净环境补足关键风险后即可。给出PASS/REQUEST_CHANGES及精确问题位置、反例、影响、建议稳定issue ID/轮次，不更改S1台账。真实GPU与Mac→SSH→Colab路径待S1后续有界smoke，本轮不得代签。交付独立报告、handoff、精确审核commit及私有证据索引。

公开交付路径固定为`reports/reviews/P07_G6_INTEGRATION_CPU_R1.md`和`coordination/handoffs/P07-g6-integration-cpu-r1.md`；私有索引随实际精确审核提交回报。不要把本任务的派发状态或作者自测改写为独立PASS。
