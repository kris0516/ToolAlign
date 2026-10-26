# 原创客户端开发示例

全部材料为公开原创 CPU scripted fixture，使用 `local-devops.v1` 固定只读工具；没有训练数据、隐藏评测题或真实模型输出。HTTP fixture 提供声明的 Action 原文，本地工具进程实际运行并回收。真实 Colab/M1 对这些输入的表现为 **NOT_RUN**。

从仓库根目录运行；每次输出使用尚不存在的私有目录：

```sh
uv run --locked python -m toolalign.client demo --cases examples/service/scripted.json --case normal --output .toolalign-local/g6-normal
uv run --locked python -m toolalign.client demo --cases examples/service/scripted.json --case no-tool --output .toolalign-local/g6-no-tool
uv run --locked python -m toolalign.client demo --cases examples/service/scripted.json --case invalid-arguments --output .toolalign-local/g6-invalid
uv run --locked python -m toolalign.client demo --cases examples/service/scripted.json --case recovery --output .toolalign-local/g6-recovery
uv run --locked python -m toolalign.client demo --cases examples/service/scripted.json --case budget --output .toolalign-local/g6-budget
```

| case | 输入与脚本 | 预期轨迹状态 | 语义结果 |
|---|---|---|---|
| normal | 1536 KiB转MiB；一次调用后final=1.5 | finalized / final | success |
| no-tool | 2+3；直接final=5 | finalized / final | success |
| invalid-arguments | 查询构建报告；脚本给出不合法的build编号999 | rejected / invalid_arguments | failure；0本地工具child |
| recovery | 构建报告首次可重试失败；新call_id重试后回答失败测试数2 | finalized / final | success |
| budget | 脚本连续请求相同换算，第三轮未给答案 | budget_exhausted / tool_round_limit | failure；只执行前两工具轮 |

输入文件为各 `*-input.json`，完整输出脚本、故障计划和预期值在 [scripted.json](scripted.json)。故障计划仅由本机示例runner设置，不是 HTTP 字段，也不能由模型指定。`run` 命令只接收 ModelInput，不读取脚本或预期答案。

`summary.json` 同时报告行为是否符合预期与语义结果。五类行为检查全部通过时 `demo` exit0，包含两条预期失败；不能将这个退出码称为模型100%成功。每类目录保留客户端决策/轨迹、原始HTTP fixture请求与进程记录。取消与远端配置见 [复现说明](../../docs/19_REPRODUCTION_AND_DELIVERY.md)。
