# P07 G6 服务与客户端集成 CPU 独立审查 R1

2026-10-27，实际审核者 **R1 AI**。结论 **PASS，新增实质问题 0**。受检实现为 `fa908839859b758ab2444845f9a2ad2c1eae6c57`；审核起点 `d259d85feb96ee8aaa5e4918e00c4f20973bf47d` 仅在其上增加任务说明与协调状态。本轮未修改生产实现、原始证据或共享台账。

生产 `RemoteClient/run_trajectory` 与生产 HTTP、调度器及 owned child 已通过实际 CPU loopback 组合：原创后端提出单位转换，本地固定工具返回 1.5，观察回传后得到 final。另一条真实请求返回两个工具调用，其中一个参数非法；服务按合法 Action 记 completed，客户端整批拒绝，工具 child 数为 0。这支持服务与客户端的执行边界，模型语义效果仍以原 G5 结果为准。

建议 S1 接纳本轮 CPU 集成证据，完成主干核对后再冻结有界真实服务 smoke。**CUDA 服务、Mac→SSH→Colab 链路及真实缓存/取消验收仍为 NOT_RUN**。

## 证据身份与复用

T1 精确提交 `185d857e94c4187b8167515bf9cdadba248960b0`，E1 精确提交 `59b9c482e0faf93b1fbd5836db21933a6d7197a1`。逐文件回读并校验 T1 的 4,586 份、E1 的 355 份私有文件，以及各自 20/24 份公共交付；公共文件与作者提交和集成候选字节一致。

复用 **179 项不同检查的通过记录**：T1 最终服务矩阵 25 项、其受影响矩阵中的 124 项通过子集、E1 最终客户端 30 项。T1 的三项既有 pip parser 跳过保持；其原失败用错 principal 的检查从通过子集排除，最终服务矩阵已有修正后的通过记录。分别核对最终服务回执的 18 个 source/test 路径、复用子集的 10 个路径和客户端最终矩阵的 16 个路径，均与当前候选一致。未重跑未受影响的训练数值、恢复或全量模型矩阵。

复用的真实原创 tiny CPU DynamicCache 五次 principal 顺序为 A/A/B/B/A：命中 tokens 为 **0/11/0/11/0**，prefill 为 **12/1/12/1/12**，输出相同。源码中的唯一 entry 以实际 ModelIdentity 和 principal 绑定；模型、adapter、tokenizer、template 不匹配不能复用，失败清除，取消或重启销毁 worker。该证据不构成 CUDA 性能测量。

## 新增独立执行

在全新 CPU 依赖环境执行 `uv sync --locked --python 3.14`，实际 Python 3.14.7；未安装 torch、MLX 或其他模型运行依赖。按文档从本 Git checkout 执行完整 `toolalign.client demo`，五类预期行为均通过：三条语义成功、两条预期失败。其决策数为 2/1/1/3/3，工具轮数为 1/0/0/2/2。

七项独立场景取得通过证据：首轮五项通过；修正两处审查脚本错误后，仅对另外两项定点复验，两项通过、五项未重跑。候选生产源码全程未改。

| 独立场景 | 实际结果 |
|---|---|
| 生产客户端、服务与本地工具组合 | 两次决策完成转换/观察/final；错误参数整批拒绝、零工具执行；篡改 advertised schema 返回 400，按该 key 查询仍 404。 |
| 排队、幂等、越权与重载截止 | 一 active/两 pending 时新增返回 429，同 key 可回读、不同 body 返回 409；跨 principal 查询/取消返回 404。queued 取消不杀 active；300ms 原截止在重载中约 310ms 终止，未派发、deadline 不变；active 取消/超时均在实际回收后终态。 |
| POST 响应晚于本地截止 | 生产服务已接收后，HTTP 回执延迟越过 180ms 本地截止；客户端只提交一次创建 POST，随后查回 timed_out/reaped。最终一个已接受请求、一次生成，没有新建替代请求。 |
| 完整父进程 SIGINT | active 和 queued 均 cancelled，summary 完整；真实 child 回收、lease 释放，父进程 exit 0。 |
| 完整父进程 SIGTERM | 同样完成有界停服、summary、child 回收及 lease 释放，父进程 exit 0。 |
| 正常父进程退出 | 完成一次请求后，由短服务总预算触发正常退出；常驻 child 已回收，lease 已释放，父进程 exit 0。 |
| 干净 CPU 用户入口 | client/service `--help`、合法配置 `validate` 成功；非 loopback 配置被拒绝，未加载模型。 |

本轮实际运行共 **28 个唯一 owned child 全部 reaped、目录清理且交付核对时 PID 不存在**：五类 CLI 示例 15 个，七个生产服务运行共 11 个，独立本地工具 2 个；包括保留的审查脚本失败运行。三个完整父进程也已回收。服务输出预算复核包含最终 summary；383 份新回执、状态与日志扫描未发现测试 token 泄漏。

组合候选实际构建 sdist 及从其重建 wheel，通过检查：两者包含 service/inference/client 全部 **18 个模块**，模块字节与候选一致，未包含私有审查目录、token 或权重。既有 sdist 白名单不含 `examples/service`，用户示例按文档从 Git checkout 取得；本轮未扩大打包范围。

## 源码与辅助脚本结论

加载就绪与当前存活 child/epoch/模型身份绑定，prepare 没有隐含生成。固定 CLI 验证 source、依赖锁和模型/adapter；真实 CUDA child 使用与训练相同的 GPULease。单 active、两 pending、64 记录、配置 attempts 和输出预留均有源码与作者执行证据；未知 usage/阶段保持 null。未确认回收分支保持 stopping/cleanup_unconfirmed 并拒绝新请求，作者对应故障注入是实际回收后模拟丢失确认，不冒记真实无法回收的实测。旧评测默认次数和预算保持。

客户端独立检查原文、ModelIdentity、request/input/payload hash、原样工具 schema、参数及 call_id；返回的 parsed/ValidatedCall 声明不赋予本地执行权。原截止后清理只做 GET/取消，未知远端清理保留 unknown。token 仅经私有文件和 header 使用，不进入返回或公开日志。

只读审阅 S1 提供的八个私有辅助脚本及 hash 绑定。`guarded_tunnel.py` 复用现有命名会话与归属检查，双端 loopback、限端口与时长，并只清理自有 SSH 进程组；`stop-service.py` 的精确 argv 与现有 launcher 一致，通过记录 PID、pidfd 和进程组身份发送 SIGTERM。bootstrap/download/monitor/launch 接口沿用已审控制路径。

补充的 `freeze-g6-run.py` 绑定 main、review 报告字节与固定 tokenizer 长度；`smoke-client.py` 的 A/A/B/B/A、一次取消、重载后请求、无工具请求和最多三次 CLI 决策，总计至多 11 次尝试。取消响应丢失不新建替代请求。脚本记录的 sequence finished 仍须由实际状态、epoch、回收和成本裁定；本轮未执行这些脚本、生成正式配置/token、连接或分配 GPU。

## 失败保留与交付

T1 原 JSON 序列化顺序断言、principal 测试调用错误、超限 packet 保留 raw 漏解析三类失败，以及 E1 原被拒响应未保留、最短预算分类和导入格式失败均保留并回读。当前最终源码与对应通过回执绑定。

R1 首轮两个失败来自私有审查脚本：原创后端误读 `ToolResult.data.value`，实际字段为 `output.converted_value`；错误配置退出码误设为 2，当前 CLI 按契约拒绝并退出 1。更正前脚本、stdout/stderr、退出码和运行制品保留，未修候选后自签，也不增加正式修订失败计数。

私有入口 `.toolalign-local/review-p07-g6-integration-cpu-r1/evidence-index.json`，含完整接收快照、源绑定、命令、七场景、进程/包核验及八脚本静态意见。精确审核 commit、索引 hash 和文件数随交接回报。只公开本报告及[交接](../../coordination/handoffs/P07-g6-integration-cpu-r1.md)；新增 issue 0，无关闭或计数变更建议。
