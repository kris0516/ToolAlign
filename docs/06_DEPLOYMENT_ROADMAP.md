# 06｜受限部署路线：Colab 服务与 Mac 客户端

2026-10-27。G6采用标准库HTTP控制面、Colab CUDA worker和Mac固定只读工具。真实链路已完成11次冻结尝试，缓存/隔离/取消与重载有据，产物回收、实例停止；实际CLI尚未生成最终答案，见[服务实测](../reports/S1_P07_G6_SERVICE_R1.md)。[复现说明](19_REPRODUCTION_AND_DELIVERY.md)提供CPU及远端入口，最终R1/Q1独立审核待接纳。

## 1. 当前分层

```text
GitHub public repository
    └─ source / contracts / original examples / aggregate reports

Colab named session（private, one active GPU job）
    ├─ immutable model + G3 SFT adapter / fixed dependency lock
    ├─ HTTP control plane（127.0.0.1 only）
    └─ owned CUDA child / GPU lease / single-entry prefix cache
             ↑ OpenSSH local forwarding from an existing session
Mac（private）
    ├─ pinned run + ModelIdentity / token file / raw receipts
    ├─ independent Action parse / advertised-schema validation
    └─ fixed read-only LocalToolExecutor / observations / bounded trajectory
```

模型只建议 Action。Mac 核对原文、参数和 call_id 后执行本次 advertised 的固定工具，实际观察进入下一步完整历史。服务端不能下发任意代码、路径或模块。训练、偏好生成和模型评测继续使用 Colab；Mac 做开发、CPU 检查、控制与分析。

## 2. 服务协议与预算

[18号HTTP契约](18_RESTRICTED_CUDA_SERVICE.md)固定存活、就绪、模型身份、提交、按key/ID查询和取消端点。除 healthz 外必须鉴权；principal由认证映射决定。相同run/principal/key与payload回读已有记录，跨principal隔离。准备完成前不ready，worker崩溃不自动重放已started请求。

一个active、两个pending、64条累计记录、一个cache entry；请求接受后至多30秒，包含排队和重载等待。启动/重载各至多120秒，服务总墙钟900秒、输出256MiB，清理尾段单列。软件记录上限不等于模型调用授权；G6真实smoke至多12次generate尝试，分配上限由 [G6协议](../coordination/tasks/P07_G6_PROTOCOL.md)约束。

Mac最多3决策、2工具轮、30秒决策预算。响应丢失先按原key查询，原截止后仅查询和取消。断网后的远端状态保持unknown，直到获得可验证终态；本地退出不表示远端回收。

## 3. 制品、启停与回滚

制品身份包括模型revision/hash、tokenizer/template、adapter、量化、训练输入与配置、代码、依赖锁及评测结果。M1固定为G3 step743；模型切换须完整停服，保留旧文件，以新run ID及新输出目录重启，进程cache随之销毁。

[19号文档](19_REPRODUCTION_AND_DELIVERY.md)提供客户端命令、私有配置格式、SSH前置和回滚步骤。本轮两端loopback端口为18761，完整SSH命令与身份留私有回执；先后台启动、退出启动连接，再建立转发，关闭隧道后才使用另一条SSH控制/回收连接。服务回滚未实测。停止前回收日志/状态与worker证据，随后停止Colab实例并确认无活动分配；本轮已有完整停止回执。断SSH不释放资源。

## 4. 质量与服务验收

模型效果依据冻结任务的语义成功、无需工具行为、参数错误和故障恢复。G5的M0/M1完整成功均0/28，服务接口完成不能改变该结论。

服务验收另查身份、鉴权、队列、原截止、取消/真实child回收、lease释放、cache失效、输出预算和网络中断。R1在干净CPU环境复现入口，并审核实际Mac→SSH→Colab链路；Q1独立检查示例与最终说明。公共CI运行CPU契约、工具、oracle、数学、打包和公开内容检查；固定模型加载与GPU运行不放入普通PR CI。

## 5. 后续路线

在当前受限交付验收后，才根据实际需求另立私有网络、多客户端负载、模型制品发布或新领域集成任务。公开源码不附带公网推理端口。长期LiDARFoodAgent衔接仍需独立隐私、接口和许可决定，不能把工具基准结果转写成健康效果。
