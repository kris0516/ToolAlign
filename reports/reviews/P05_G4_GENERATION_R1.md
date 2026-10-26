# R1｜G4 CUDA 候选生成 CPU 实现审查

2026-10-26。**PASS（CPU 实现技术审查）**。本轮新增 P0=0、P1=0、P2=0。支持 S1 接纳生成实现；真实 CUDA 冷加载、候选吞吐和 30 秒内的可用产出须由后续冻结的 pilot 实测。

精确候选为 `d1aa1c8e542898173455afbfa72d09fc3faaa9b7`；审查授权与实际受检源码为 `f72bb5fc7343989efcfc01b305e690d0cddeb661`。依照[本轮任务](../../coordination/tasks/P05_G4_GENERATION_R1.md)和[G4 协议](../../coordination/tasks/P05_G4_PROTOCOL.md)，核对候选全部 15 个交付文件与受检版本逐字节相同。跨两包的源码、输入与既有证据共 80 项绑定全部通过。

## 实现判断

- `CUDAGenerationBackend` 在 owned child 内按需加载，收到的请求为 `ModelInput` 与 `GenerationConfig`。加载路径固定 CUDA、1.7B 的选中 step743、checkpoint/adapter 身份及逐键形状检查；BF16 底座、FP32 LoRA 的加载复用 G3 实现，没有 CPU 模型回退。
- 完整 messages、工具 schema 和模板进入编码；输入 token 数加 256 生成预留不得超过 2048，越界在模型加载前失败。默认 greedy 行为保留，G4 显式使用 temperature=0.7、top_p=0.9、max_new_tokens=256、enable_thinking=false，并按完整候选计划分配 seed。
- harness 记录实际发送的 `decision_inputs`，每条成功返回的 decision 绑定其输入 hash。后续调用在后台失败时，已发送输入可以比已返回 decision 多一条；这类记录保留并作为非语义终止排除。3 decisions、2 tool rounds、256 tokens、30 秒边界保持。
- 每候选新建工具执行器与 faults 状态。启动前先持久化 `started`；恢复遇到已启动但无终态的候选登记 `interrupted`，不重跑或覆盖旧终态。全计划、全局候选顺序、seed 与失败分母固定。
- Colab 控制器只开放指定 generation 模块，验证真实轨迹、时间和输出预算；既有 SFT 分支保留。owned child 继承外层进程组，停止与导出仍要求确认该组已回收。

## 独立 CPU 证据

双包合计 **4 passed，0 failed，0 skipped**，分两次执行为 3 passed / 1.43 秒和 1 passed / 0.37 秒。以下三项直接覆盖生成器及其集成；另一项分组隔离见[偏好审查](P05_G4_PREFERENCE_R1.md)。不将共享检查重复累计。

| 独立检查 | 实际结果 |
|---|---|
| 原创 scripted fixture 经实际 `run_batch` 生成 4 条，再交给 D1 提取器 | 子进程检查请求字段及 seed 42–45、全部采样参数；4 条实际输入和 decision hash 对应。有限 oracle 未枚举的合法替代记为 unknown，后台异常与格式失败记为非语义终止；偏好数 0、候选分母仍为 4，全部进程回收。 |
| 恰好 2048 的上下文边界 | 合成 1792 个输入 token 加 256 预留到达加载入口标记，随后在任何模型加载前主动停止；没有越界拒绝或截断。复用 T1 已有 1793+256 拒绝证据。 |
| 外层 Colab 停止与实际 owned model child 组合 | CPU wrapper 启动真实子进程并确认同一 PGID；调用未修改的 `terminate_owned_group` 后，wrapper 返回 124，trace 为 cancelled，child 已 reap，sandbox 为空且进程组不存在。 |

另独立回读 S1 已保存的 2→4 候选恢复产物：原终态字节保持，受检源码一致。仅对这 4 条既有记录重做提取，得到 1 对 synthetic 偏好，双方 seed 为 42/43。没有重跑 S1 原集成 pytest 或追加该组候选。

复用并核对 T1 原回执：回归 170 passed、2 skipped；最后统计文件回收修改另有 18 passed。两项 skip 为既有 pip parser 检查。日志摘要、源码索引与最终改动覆盖均已核对，未重跑完整矩阵。S1 原语料 tokenizer 预检的最大初始/脚本后续输入为 1351/1742 tokens，均可容纳 256 预留；R1 只核对其固定输入和回执，修订语料须重新绑定。

本轮私有 `evidence-index.json` SHA-256：`cd9e52b0291d5ffa414216e8fe7fc53cc7a3d85f0b54336c3262fbadcf48ec55`。索引绑定两个独立测试脚本、命令回执、实际结果和补充回读材料；复现入口见[交接](../../coordination/handoffs/P05-g4-generation-review-r1.md)。

## 后续边界

Q1 语料 r1 提交 `fd0e8f34f3e7bf80d70914e5177d84cc8386a50e` 为 **REQUEST_CHANGES**：`Q1-G4-CORPUS-001 / P2` 指出第 10、13 项提示未明确版本值须为 JSON 字符串，封闭答案却排除数值等价表示。该问题由 D1 定点修订、Q1 复核；本 CPU 实现 PASS 不关闭它，也不重复登记为新增 R1 问题。

本轮未改变生产代码、数据、依赖或共享状态；原失败历史保留。没有模型加载、依赖安装或 GPU 分配。G4 真实 CUDA 生成、正式偏好池和 DPO 均 **NOT_RUN**。S1 接纳 CPU 实现并完成语料修订验收后，按既定预算冻结 pilot；本报告不扩展运行授权。
