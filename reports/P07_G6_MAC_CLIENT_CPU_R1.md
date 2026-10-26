# E1｜G6 Mac客户端与交付说明 CPU r1

2026-10-27。客户端最终 **30项CPU检查通过**：实际loopback鉴权、原key恢复、原截止后的只读查询/取消、SIGINT回收、身份/原文交叉检查和本地固定工具边界均有执行证据。五类原创脚本行为符合预期，其中3条语义成功、2条预期失败；示例的5个本地工具child和10个远端CPU fixture child均已回收。

本轮没有加载固定模型、分配GPU或启动Colab。T1生产服务组合、干净环境独立复现、真实SSH/CUDA服务及R1/Q1终验仍待S1组织，不以CPU fixture代替。

## 范围与实现

起点为S1协议提交 `ef885c035f2b08a5ad781f040d4ee8867f2c79ba`，分支 `codex/e1-p07-g6-mac-client-r1`。新增 `toolalign.client`、对应测试和 `examples/service`；更新README、06/08/10与新19号说明。service/inference、model_io、工具registry/executor、冻结契约、依赖锁、训练/评测输入及共享协调状态保持不变。

`python -m toolalign.client`提供`run/cancel/demo`。标准库HTTP只连接显式端口的literal loopback，不使用代理或跟随重定向；token从私有0600文件读入header。提交前核对固定run/ModelIdentity、catalog、协议限制及loaded-ready。原key/body先落盘，丢失响应以原key恢复，截止后不再创建请求；无法确认远端状态时保留unknown。

客户端独立parse原文并与服务返回字段核对，完整保存raw/usage。工具必须属于本次advertised原样schema子集，整批参数及call_id先验证，再通过现有一次性ValidatedCall/LocalToolExecutor执行。完整观察和schema/history用于下一决策；最多3决策、2工具轮、30秒，显式远端清理另有预算。没有修补原文、强制final或自动工具重试。

`scripted.py`为本包原创开发HTTP fixture，实际spawn CPU child并回收；identity/usage为合成值，无生产GPU调度、cache或lease验收含义。CLI脚本答案判定与API completed分开；真实run的语义结果为not_scored。

## 实际验证

环境为已有macOS26.5.1 arm64、Python3.14.7基础环境，依赖未修改。最终命令：

```sh
.venv/bin/python -m pytest -q tests/client --basetemp .toolalign-local/p07-g6-mac-client-r1/pytest-final
```

结果为 **30 passed / 7.48秒**。测试通过独立子进程执行用户CLI，通过真实HTTP丢弃/延迟响应与SIGINT触发边界，不mock客户端传输或本地工具执行器。

| 检查 | 已观察结果 |
|---|---|
| POST已接受但响应丢失 | 原key查回，1个已接受请求、1次生成 |
| 原POST未到达 | 原截止内重发同key、相同body，不提高timeout |
| 原POST延迟至本地截止后 | 仅按key查询/取消；晚到且接受者回收，未到达者保持unknown |
| 控制网络断开 | 本地超时，远端cleanup仍unknown |
| CLI SIGINT与后续cancel | 退出130，实际CPU child取消/reaped；手动cancel不新建决策 |
| 鉴权与身份 | 错误token/run/model均在POST创建前拒绝；代理/redirect不收到token |
| 不受信动作 | 非advertised工具、错误参数、重复call_id和篡改schema均拒绝；整批预检阻止部分执行 |
| 不一致响应 | raw解析、model、payload或回收声明不一致时拒绝，原响应保留；无本地工具child |
| 原文/截止 | Markdown包裹原文保持parse_failure；慢速HTTP头不延长总截止；1毫秒预算记timed_out |

五类CLI例子的决策数为2/1/1/3/3、工具轮数为1/0/0/2/2；恢复案例的首次观察为retryable错误，脚本随后以新call_id重试。预算案例第三个工具动作保存但不执行。具体输入、脚本、命令见 [示例说明](../examples/service/README.md)。

交付检查全部exit0：全仓Ruff、4文件冻结契约、1008路径公开内容扫描、63条本地Markdown链接与24文件范围核对。实际sdist、直接wheel和从sdist重建的wheel均排除241个私有canary并保留18个公开fixture及冻结schema；sdist为264文件、628993字节。另核对66份生成的私有token均未进入公开改动或JSON回执。未重复未受影响的训练数值或全量模型矩阵。

## 原始失败与修复

首次新增边界测试为24 passed / 4 failed：四种不一致响应均正确拒绝并阻止工具执行，但原响应没有进入回执。增加`rejected_response`保留首个被拒绝的对象，原四项定点复验通过，最终30项再次覆盖。

补充最短CLI预算检查首次为1 passed / 1 failed：不足1毫秒的剩余时间被整数取整后当成输入拒绝。现由原单调截止进入timeout/cancel流程；定点1项及最终检查通过。首次Ruff只有1项导入格式错误，修后通过。全部原stdout/stderr、返回码和对应源码身份保留；这些是实现自测记录，不冒记独立审核轮次。

## 说明绑定与结果边界

[19号文档](../docs/19_REPRODUCTION_AND_DELIVERY.md)包含用户入口、私有配置、SSH前置、取消/启停与撤回。首个服务之前的稳定代码为PR34 main `98d642a116da94f2ab2b2aaeb6e931f79fd5cabc`，它包含SFT/评测但没有可启动旧服务；撤回G6后服务关闭，重新提供服务须使用已验收G6源码和新run/config。

只读回真实13例数组中的formal/train `effective-09`：P1724、Action108+EOS1、bucket2048、109个监督target，因果监督位置1723–1831。数组/原行/sequence/mask身份与真实G5失败unit6已写入私有`documentation-bindings.json`，无新tokenizer编码。DPO使用既有原创标量案例并独立回算0.6931471805599453与0.6443966600735709，实际SUM/mask/reference证据沿用原独立审查；不是实际训练偏好对。两份固定Qwen revision的官方LICENSE已核对为Apache-2.0。

G5 M0/M1完整成功均0/28，A1 on/off均0/8；A2支持局部prefill复用。G4零有效偏好，DPO/M2未运行；L2零合格、无官方模型分数。上述失败与成本保持。真实G6服务示例、撤回/重启、远端成本仍NOT_RUN；Q1最终说明审阅未发生，不记录为kris本人审核。

## 交付入口

私有目录为`.toolalign-local/p07-g6-mac-client-r1/`，`commands/`保存命令与原始结果，`pytest-final/`保存最终CLI/HTTP/child证据，`evidence-summary.json`与`documentation-bindings.json`保存汇总与来源，`handoff-index.json`绑定最终提交、公开文件与全部本地证据。公开仅含原创示例和摘要，无凭据、原始训练数据、隐藏题面/答案或模型文件。

复现按Git checkout进行；既有sdist白名单不包含`examples/service`，wheel提供客户端代码，示例从对应Git提交取得。本轮按范围未修改打包配置。后续由S1接入T1生产服务，再交R1/Q1独立审核，见 [交接](../coordination/handoffs/P07-g6-mac-client-cpu-r1.md)。
