# 19｜受限客户端复现与交付

2026-10-27。Mac→SSH→Colab L4固定M1服务已完成11次冻结尝试，实际缓存命中、principal隔离、active取消与新worker重载有据；产物已回收，实例已停止。真实CLI两次工具换算正确，但未生成最终答案，见[实际服务报告](../reports/S1_P07_G6_SERVICE_R1.md)。干净CPU复现已由R1通过，最终R1/Q1材料审核待接纳；部署回滚仍NOT_RUN。五类原创scripted示例不加载模型，客户端自测与原始失败见[CPU交付报告](../reports/P07_G6_MAC_CLIENT_CPU_R1.md)。

## CPU 用户入口

在仓库根目录使用已锁定的 CPU 环境：

```sh
uv sync --locked --python 3.14
uv run --locked python -m toolalign.client --help
uv run --locked python -m toolalign.client demo \
  --cases examples/service/scripted.json \
  --output .toolalign-local/g6-demo
```

输出目录须全新且位于 `.toolalign-local` 下；重做示例时另取目录名。`demo` 启动本机原创 CPU HTTP fixture，实际经过鉴权、客户端、独立 Action parse 和 `LocalToolExecutor`。fixture 的模型身份、usage 和响应都是合成值，不具有 CUDA/cache/服务容量测量含义。工具结果来自固定只读 fixture 数据，未连接真实 DevOps 账户。

五类案例和逐类命令见 [examples/service](../examples/service/README.md)。正常调用、无需工具和一次可重试故障可完成预定答案；错误参数和预算耗尽按预期失败。`summary.json` 的 `expected_behavior_passed` 与 `semantic_outcome` 分开：拒绝非法调用的检查 PASS 不代表任务成功。真实 `run` 不加载答案，`semantic_outcome=not_scored`；返回 `final/clarify/refuse` 只使轨迹成为 `finalized`。

每次决策保留 `decision-NN.json`：完整 ModelInput、原 key/body、request_id、HTTP 状态、服务返回的原文/usage、独立 parse 结果和取消结果。`trajectory.json` 保留本地观察、进程回收、预算和最终状态。异常字段与原文不一致时保存 `rejected_response`，没有工具执行权。凭据只保存在权限为0600的私有 token 文件并进入 Authorization header，不进入命令行、回执或 stdout。

## 连接固定远端服务

S1 提供经批准的精确源码、`toolalign.service-run.v1` 私有配置、冻结 M1 制品、依赖锁、认证映射与实际端口；配置须声明 `authorized_by=S1`、`run_kind=serving`。本轮真实运行版本为[PR35 main `aaab017`](https://github.com/kris0516/ToolAlign/commit/aaab0171246feaf307ad2c626108e94383e438d9)。固定服务入口为：

```sh
python -m toolalign.service serve --run-config "$TOOLALIGN_SERVICE_RUN_CONFIG"
```

服务只绑定Colab `127.0.0.1`。用现有包装先检查`sessions/status`，确认本任务命名会话存在、SSH alias指向该会话，且包装在会话缺失时失败；不能用官方CLI的缺省自动创建路径代替这一步。先通过控制器在tmux内启动服务，退出启动连接，再建立转发。本轮CLI 0.7.4的实测限制为同实例仅一条活动SSH：隧道存在时另开启动连接返回HTTP429。没有重复启动模型，原失败已保留。

经S1冻结的私有control spec对应下列既有入口；`setup`只在该run尚未安装时执行，连接中断后先`status`确认原作业状态：

```sh
python scripts/colab/control.py --spec "$TOOLALIGN_CONTROL_SPEC" setup
python scripts/colab/control.py --spec "$TOOLALIGN_CONTROL_SPEC" launch
```

OpenSSH转发形式如下，三个变量由实际私有回执填写：

```sh
ssh -N -o ExitOnForwardFailure=yes \
  -L "127.0.0.1:${TOOLALIGN_LOCAL_PORT}:127.0.0.1:${TOOLALIGN_SERVICE_PORT}" \
  "$TOOLALIGN_EXISTING_SSH_ALIAS"
```

本轮实际两端loopback端口均为18761，完整SSH argv、会话归属、HTTP原始回包和模型身份留在私有回执。该实例已停止；重现需要经批准的新命名会话和新run/output，不能重放旧started请求。安装、启动、空闲、传输与清理均计入资源账目，流程见[16号文档](16_COLAB_WORKFLOW.md)。客户端没有申请实例、换模型或重启服务的功能。

将 S1 交付的 token 放入私有0600文件；配置中的 `token_file` 相对配置文件目录解析。以下为配置格式，`18080` 和 run ID 是待替换示意值，七字段 M1 身份来自已回收 G5 实测：

```json
{
  "schema": "toolalign.mac-client.v1",
  "url": "http://127.0.0.1:18080",
  "service_run_id": "S1-frozen-run-id",
  "token_file": "token.txt",
  "model_identity": {
    "model_id": "Qwen/Qwen3-1.7B",
    "model_revision": "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e",
    "model_hash": "e77fd855eb6fc6ac5454700c50d890829b611b18285ced3dfd29c557d514e6c6",
    "adapter_hash": "973c440e29090892ad11d6d56b94bad4c98a5398c223e2b4302d7dba7c4640ed",
    "tokenizer_hash": "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4",
    "template_hash": "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8",
    "quantization": "none"
  }
}
```

服务就绪后，实际客户端入口为：

```sh
uv run --locked python -m toolalign.client run \
  --config .toolalign-local/g6-private/client.json \
  --input examples/service/normal-input.json \
  --output .toolalign-local/g6-request-01 \
  --seed 42 --timeout-ms 30000 --cleanup-ms 5000
```

`run` 最多3次模型决策、2工具轮，共享一个至多30秒的单调截止。服务采样固定为 temperature=.7、top_p=.9、top_k=0、thinking=false、256输出；完整输入加256必须不超过2048，不截断 schema/history。客户端核对 run/ModelIdentity、完整 catalog hash、就绪和协议参数，再独立解析 `raw_text`；整批调用均通过 advertised 原样 schema、参数和未重复 call_id 检查后才取得本地一次性 `ValidatedCall`。固定工具由 Mac 执行，服务不能指定本地路径、模块或代码。

## 丢失响应、取消与停止

客户端先持久化原 key/body，再提交请求。POST 响应丢失后以同 key 查询；仅在原截止内确认查无记录时才可用原 key/原 body 重发。本地截止后只有按 key 的只读查询与 cancel，不新建请求。所有连接、响应读取和轮询共用原截止。

运行中按 Ctrl-C 会请求取消，默认额外等待至多5秒确认远端状态。`decision_seconds` 为轨迹从开始到完成、取消或截止的决策时间；`cleanup_seconds` 单列其后的收尾时间，二者之和为 `complete_wall_seconds`。`remote_cleanup_seconds` 单列显式远端清理；本地工具的 `call_seconds_including_cleanup` 包含其执行器回收。正常工具回收可能发生在决策预算内，不能把这几个重叠口径相加。

网络中断且无法确认远端状态时保留 `resolution=unknown`。连接恢复后可用原回执继续查询/取消，输出用新目录：

```sh
uv run --locked python -m toolalign.client cancel \
  --config .toolalign-local/g6-private/client.json \
  --request .toolalign-local/g6-request-01/decision-00.json \
  --output .toolalign-local/g6-cancel-01 --cleanup-ms 5000
```

该命令不会创建新决策。`terminal_observed` 表示已回读终态；正常 completed 的 worker 可以为 `live` 以复用 warm/cache，因此不能把该字段称为“worker已回收”。active cancel/timeout 的终态必须有 `reaped` 证据，queued 取消可以为 `not_started`。

`run`退出码0表示finalized，1表示未完成，130表示用户取消；2表示输入、配置或本地I/O拒绝。`cancel`退出码0表示读到终态，1表示未确认。关闭转发隧道后才使用另一条SSH控制连接。服务到预设墙钟期限会停止；如提前停止，只向已核对argv/进程身份的服务父进程发信号，不能按名称杀其他作业。本轮在生成次数上限已回收child后用定向SIGTERM结束HTTP父进程，退出0。

先确认服务终态及child/lease释放，再回收并停止实例：

```sh
python scripts/colab/control.py --spec "$TOOLALIGN_CONTROL_SPEC" status
python scripts/colab/control.py --spec "$TOOLALIGN_CONTROL_SPEC" recover
python scripts/colab/control.py --spec "$TOOLALIGN_CONTROL_SPEC" stop
```

`recover`回读完整manifest与字节后确认，`stop`核对全部run已持久化并验证实例缺席；关闭SSH本身不会释放实例。重试前检查已有receipt，不能把连接失败当成作业失败后直接重新提交。

## 模型制品、许可与回滚

M1 为 Qwen3-1.7B 原始指令 checkpoint 加 G3 step743 LoRA，完整训练状态 SHA256 为 `cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14`。BF16 底座未量化，Q/V 28层 rank8、alpha16、dropout0，adapter 为FP32。0.6B用于G3冒烟，1.7B用于正式SFT；两者各完成一轮。训练与选模证据见 [G3报告](../reports/S1_P04_CUDA_G3_SFT.md)，固定依赖见 [CUDA锁](../requirements/cuda-linux-py312.lock.txt)。

官方固定 revision 的 [Qwen3-0.6B LICENSE](https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/LICENSE) 和 [Qwen3-1.7B LICENSE](https://huggingface.co/Qwen/Qwen3-1.7B/blob/70d244cc86ccca08cf5af4e1e306ecf908b1ad5e/LICENSE) 均为 Apache-2.0，已回读核对。仓库原创代码/文档为 [MIT](../LICENSE)，数据、模型和依赖保留各自来源与条件，见 [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md)。公开交付不包含模型权重、adapter、原始训练数据、隐藏题面/答案或 token。

首个G6服务之前的已验收代码为 [PR34 main `98d642a116da94f2ab2b2aaeb6e931f79fd5cabc`](https://github.com/kris0516/ToolAlign/commit/98d642a116da94f2ab2b2aaeb6e931f79fd5cabc)，包含SFT与评测，尚无可启动的旧服务。可恢复的模型基准为已验收的G3 step743，原文件保留。

撤回G6时，先停止接受新请求、取消/回收child并归档本run记录，再恢复上述稳定代码、匹配配置/依赖及保留的G3制品。恢复到该版本后服务保持关闭。若后续重新提供服务，须采用已验收的G6源码，以新run ID、新输出目录和匹配的客户端固定配置启动；进程重启自然销毁cache。旧started请求不自动重放。**G6撤回与服务重启实测仍NOT_RUN**；保留step743或同模型child重载都不构成已部署旧服务的回滚证明。

## 一条真实训练样本的 token/mask

采用既有13例材料中的 `effective-09`，它确实进入 formal/train。其原历史角色为 `system,user`；工具声明、原历史及 assistant 前缀共 `P=1724` tokens，当前 Action JSON为108 tokens，再追加1个EOS，总长1833，padding bucket为2048。以下为零基、含端点位置：

| 原序列位置 | 内容 | attention | loss mask |
|---|---|---:|---:|
| 0–1723 | 完整 prompt 与模板 | 1 | 0 |
| 1724–1831 | 当前 Action JSON | 1 | 1 |
| 1832 | EOS | 1 | 1 |
| 1833–2047 | 215个pad | 0 | 0 |

因果移位后 `input=ids[:-1]`、`target=ids[1:]`、`causal_mask=loss_mask[1:]`，监督位置为1723–1831，共109个有效 target。SFT CE按这109个目标归约；历史工具观察如存在，也属于 prompt。该样本拟合的是当前工具调用，不提供最终回答能力的直接证据。

原JSONL行 SHA256 为 `2e9241b0f40c329bce7dc645b1ab4247ad53569e70ed6b6b856c6ab7c7778fb3`；sequence SHA256 为 `ac332634ae1afd01de5da4838a5cbe3ad099bfc7a78c499e4a543a60ae463205`。绑定 [真实v3消费报告](../reports/S1_P04_DATA_V3_CONSUMPTION.md)中的数组 export `cc82ba3c…649d3` 与 manifest `71204d7b…064d4`。本次只读回数组和 mask，无新编码、无模型加载；原文与token IDs继续留私有。

## DPO 的原创数值说明

设 `sθ(y|x)` 为 completion 有效 token（含EOS）的 log probability **之和**，prompt/pad不参与。冻结 reference 为选中 SFT 模型，adapter保持启用；policy和reference独立加载。目标为：

```text
margin = (sθ(chosen) - sθ(rejected)) - (sref(chosen) - sref(rejected))
loss = -log sigmoid(0.1 × margin)
```

下表沿用 [已验证原创标量案例](../tests/training/compatibility/test_invariants.py)，再次以标准库独立公式回算；它没有实际 chosen/rejected 训练文本：

| 阶段 | policy chosen/rejected SUM | reference chosen/rejected SUM | margin | loss |
|---|---|---|---:|---:|
| 同起点 | -2 / -3 | -2 / -3 | 0 | 0.6931471805599453 |
| 增加chosen相对概率 | -1 / -3 | -2 / -3 | 1 | 0.6443966600735709 |

不能把 SUM 换成 token mean：不等长 completion 会改变目标。原生 TRL/独立CPU参考的实际 mask、EOS、SUM和梯度验证见 [R1数值审查](../reports/reviews/P05_G4_DPO_R1.md)；其FP64 SUM loss为0.6860301000108073，错误token-mean对照为0.6930230114156783。原输出预算问题与 [r2关闭记录](../reports/reviews/P05_G4_DPO_R2.md)保持可追溯。实际G4的80条候选产生0个有效偏好，DPO CUDA训练及M2 checkpoint均NOT_RUN，不能拿该数学例子当作已训练成果。

## 实测结论与一个失败边界

G5固定28题中M0/M1完整成功均0/28；首动作格式合法为1/28和28/28。M1的66个合法动作全为tool_calls。A1恢复on/off均0/8；开启时8次重试取回观察，仍未完成任务。A2的12对原始输出相同，4次真实cache命中，命中prefill缩短34.70–39.49毫秒；总耗时91.175→91.006秒，其中一次命中请求总耗时反而增加39.01毫秒，证据支持局部prefill收益。L2的150条固定输入筛选后0合格，官方模型分数不定义。见 [完整G5报告](../reports/S1_P06_G5_EVALUATION_R1.md)。

真实失败 `unit_id=6/M1` 属于无需工具题：前两次动作各调用2个工具，第三次完整输入增至1991 tokens，加256输出预留为2247，超过2048；以 `backend_error/context_overflow` 结束，没有最终答案。5个owned child均已回收。原结果文件 SHA256 为 `001709eac0905a9bf279396ad1d3c1b288ca9a6af3d1c47c51e65ce1f2cf0a89`，该行 SHA256 为 `6c270503c22528a801498e63bd2d3ff34f3eaadf570d003bb85b039f0f02dcf2`。这说明格式正确与工具执行完成仍不足以决定何时停止；客户端保留失败，不压缩历史或补写final。隐藏题面与答案未复制到开发示例。

G5分配实际2358.235秒、余额观测差0.89 CU。G6本轮唯一L4分配837.615秒、余额166.20→165.95 CU，71份远端文件已回收、实例已停止；采样显存峰值3856 MiB，CUDA allocated/reserved峰值3469.662/3592 MiB。实际11次尝试为10 completed、1 cancelled；完整CLI14.378秒后因工具轮次上限未完成，不能把API completed当作任务成功。两次同principal缓存各命中580 tokens，跨principal及重载后均miss。计时口径、缺失计量与原失败见[完整报告](../reports/S1_P07_G6_SERVICE_R1.md)。累计7200秒/4CU、首次3600秒、单服务900秒/256MiB为原上限。

## 交付与独立复核

从[CPU交接](../coordination/handoffs/P07-g6-mac-client-cpu-r1.md)取得精确客户端提交、命令及私有索引；[G6实测](../reports/S1_P07_G6_SERVICE_R1.md)绑定实际源码、冻结配置和完整回收。两个完整G3训练checkpoint及本轮原始回执由S1私有交付索引定位。最终独立接纳与GitHub最后版本读回登记到[PROJECT_STATUS](../coordination/PROJECT_STATUS.md)。

R1负责精确集成候选、干净CPU环境及真实远端链路的技术验收；独立Q1 AI核对示例、上述样本/数学/失败说明与实际证据。执行 [REVIEW_POLICY](../coordination/REVIEW_POLICY.md)，不记作kris本人签字或掌握程度证明。
