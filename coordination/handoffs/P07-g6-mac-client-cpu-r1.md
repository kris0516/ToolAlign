# E1 → S1｜G6 Mac客户端 CPU r1

2026-10-27。从 `ef885c035f2b08a5ad781f040d4ee8867f2c79ba` 开始，分支 `codex/e1-p07-g6-mac-client-r1`。精确交付提交由本次回报及私有 `handoff-index.json` 登记；不修改共享状态或自行合并。

交付包括标准库loopback客户端、固定只读工具轨迹、五类原创CPU示例、README/06/08/10更新与 [19号复现说明](../../docs/19_REPRODUCTION_AND_DELIVERY.md)。[实现报告](../../reports/P07_G6_MAC_CLIENT_CPU_R1.md)记录30 passed、两类实质自测失败及修复；5个本地工具child和10个示例CPU child全部回收。真实模型加载/Colab分配为0，T1服务组合及G6实际运行/独立终验尚未执行。

建议R1在精确集成候选的干净CPU环境运行：

```sh
uv sync --locked --python 3.14
uv run --locked python -m toolalign.client demo --cases examples/service/scripted.json --output .toolalign-local/r1-g6-demo
uv run --locked pytest -q tests/client
```

然后针对T1真实服务组合核对：固定run/model/catalog、ready、按原key查回、原截止后只读取消、active回收与lease释放、完整历史/工具观察。E1的HTTP fixture明确为原创CPU开发材料，不验证T1的生产队列/cache/GPU行为。已有训练数值、G5结果和独立审核精确身份已绑定，未变部分可复用。

Q1核对五类案例的行为检查与语义结果区别、真实`effective-09` mask、原创DPO数值与冻结SFT reference、G5 unit6失败及当前0/28/0偏好/L2处置。实际审阅者记为独立Q1 AI；本交付不宣称已通过其审核。S1已要求明确首版撤回至PR34稳定代码后服务关闭，说明已落实；不新增正式问题或失败轮次。

本地证据入口：`.toolalign-local/p07-g6-mac-client-r1/handoff-index.json`。索引覆盖命令/返回码/源码hash、原失败、最终CLI与真实child记录和只读来源绑定。旧证据保持，未写入S1来源目录。公开复现使用Git checkout；原sdist白名单没有`examples/service`，本轮未越范围修改打包配置。

下一步由S1集成、组织R1/Q1并冻结真实GPU smoke；实际端口、命名会话、SSH完整命令、服务回滚/重启与最终GitHub版本由该阶段真实证据补齐。
