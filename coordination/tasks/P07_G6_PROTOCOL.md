# G6｜受限 CUDA 推理、复现与交付协议

2026-10-27，S1。G5已按真实负结果与明确缺项验收；PR34主干`98d642a116da94f2ab2b2aaeb6e931f79fd5cabc`与受检头文件树一致，双Python CI 40400234474全部通过。R1 `b52c711` / Q1 `c4ef464`终验已接纳，G5 App goal实际complete。G6为唯一active goal。本协议授权先完成CPU实现和独立审核；实际GPU运行清单由S1在这些前置条件完成后冻结。

## 固定结果与边界

交付可运行的Colab loopback CUDA服务、Mac SSH转发客户端、固定工具执行边界、复现说明和GitHub精确版本。M1固定为Qwen3-1.7B原revision及G3 step743 adapter，沿用BF16、未量化、原模板、temperature 0.7 / top_p 0.9 / top_k 0、thinking=false、每请求256输出和2048上下文。模型身份见[G5报告](../../reports/S1_P06_G5_EVALUATION_R1.md)。

G5的M0/M1完整成功均0/28，首动作格式合法1/28与28/28；8次恢复重试未产生完整答案；A2支持局部prefill复用。M2没有DPO checkpoint，L2没有官方模型分数。服务完成不改变这些事实；不得追加训练、选测试样本、强制final或修复原文来制造成功。

## 共享接口与所有权

[HTTP契约](../../docs/18_RESTRICTED_CUDA_SERVICE.md)在两实现包开始前冻结。新服务版本为`toolalign.service-http.v1`和`toolalign.service-run.v1`，不修改已有冻结契约。启动CLI固定`python -m toolalign.service serve --run-config <private JSON>`；run配置声明`authorized_by=S1`、`run_kind=serving`，不能从客户端指定模型、路径、模块或采样。token文件、权重、原始输出与实际run配置留私有。

| owner | 范围 |
|---|---|
| T1 | service/inference持久worker与HTTP；必要CUDA prepare/lease/cache接缝；Colab support固定白名单/预算适配及相应CPU检查 |
| E1 | 独立Mac client、固定只读工具桥接、原创开发示例、README和复现/交接说明 |
| R1 | 精确集成候选的独立技术审核、真实负向/取消/锁复核、干净CPU环境复现；实际GPU后审核已回收全链路证据 |
| Q1 | 实际示例、模型效果/成本、token-mask与DPO/reference解释、最终说明审核；真实标注AI身份 |
| S1 | 共享HTTP/范围裁定、状态维护、集成、唯一GPU运行、证据接纳、GitHub读回与最终交接 |

T1和E1最多两个实现任务并行，使用既有独立Codex对话和隔离worktree，保持gpt-6-astra/max；禁止sub-agent。接口变化先由S1协调，不各自添加字段或复写对方目录。旧P07 MLX任务不恢复。

## 最小运行边界

优先stdlib HTTP/JSON，复用CUDA解码、PrefixCache、OwnedProcess、GPULease和固定registry。服务只在`127.0.0.1`监听，经已存在命名Colab会话的OpenSSH本地转发连接；不开放公网端口。真实GPU child持lease，HTTP控制面独立于串行模型调度；一个active、至多两个pending、64条累计记录、一个cache entry。principal来自认证映射，通过IPC进入cache身份；同run/principal/key的同payload回读，不重新生成，不同payload拒绝。

prepare加载及身份核对后才ready，不用隐含生成代替加载握手。启动/重载各最多120秒，总服务墙钟900秒、输出256MiB。请求30秒为接受后含队列、重载等待和生成的决策截止；清理尾段另计complete wall。总截止前5秒开始停止/回收，Colab外层900秒硬限收尾；未确认回收保持unknown，不写成成功。服务崩溃不自动重放started请求。模型切换须完整停服/重启，旧制品保留、cache自然销毁。

Mac独立parse原文，核对本次advertised schema原样子集、参数、call_id与本地固定只读registry，再执行工具。服务端不能下发任意代码或路径。客户端以原key恢复丢失响应，负责远端cancel/poll；网络中断时不能把本地进程退出写成远端回收。演示轨迹最多3次决策、2工具轮、30秒决策预算，清理尾段单列；模型失败保留，不用scripted结果填补。

## CPU与独立验收

实现前把边界变为可执行检查。至少覆盖真实loopback鉴权、原样schema子集、同/异principal幂等与查询、队列/截止不重置、loaded-ready顺序、active取消后的真实child回收和GPU锁释放、身份/cache切换、输出预算及Mac拒绝不受信工具。可用原创CPU worker复现进程/网络行为；它不代表CUDA模型效果。共享数值与旧评测行为没变时复用既有检查，不重跑全量GPU矩阵。

E1提供原创scripted示例，覆盖正常调用、无需工具、错误参数、故障恢复和预算终止，并保留每类原始输入、输出、状态和命令。R1在干净CPU依赖环境运行用户入口及至少一个真实负向案例，检查发布内容。独立审核问题沿用[五次规则](../REVIEW_POLICY.md)，第1–4次自主修订，保留实际失败。

## 真实GPU验证与资源上限

固定M1、同2048配置与单prefix entry沿用G5容量依据：采样峰值最高3,926/23,034MiB，最长实际序列1,825 tokens。预计服务工作集不超过6GiB，L4仍留充足余量；该估算不声称已测满2048解码。CPU/R1与主干通过后执行一次固定开发smoke，不重复完整评测或容量矩阵。

全部G6分配累计上限7,200秒和余额观测4CU；初始单次3,600秒，包含安装、失败连接、空闲、传输和回收。真实generate尝试最多12次，取消/异常也计入；软件64条记录能力不授权用满64次模型调用。首个输出前冻结新开发请求、顺序、seed、run配置、cache与active取消判据。首请求测冷cache，启动冷加载单列；后续核验warm、实际命中、principal隔离、active取消及新child重载。不得用G5隐藏题/答案/输出构造训练或选择新结果。失败不私下补跑。

结束先回收完整原始证据，再停止实例并确认无活动分配。R1审核真实Mac→SSH→Colab链路与账目，Q1审核实际示例及说明；不额外开第二实例只为重复已有验证。既有资源授权不包括购买/充值。

## G6完成条件

接口和客户端可运行；CPU边界与实际CUDA smoke证据齐全；干净CPU环境复现、R1/Q1独立终验通过；README、复现入口、模型身份/许可、失败/成本、恢复上一稳定制品的方法及精确GitHub版本可读。实际训练样本的token/mask解释须绑定现有证据；DPO说明用已验证原创数学例子并明确实际偏好为0、无DPO checkpoint。Q1承担原要求的最终材料检查，不代签或声称用户本人掌握。

公开只含代码、契约、原创开发示例、聚合证据和说明；原始数据/隐藏测试/训练权重/adapter/凭据不发布。完整交付后才将G6 App goal设为complete。
