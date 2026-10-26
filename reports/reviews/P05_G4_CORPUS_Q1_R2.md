# P05 G4 语料类型约束 Q1 定点复审 r2

结论：**Q1-G4-CORPUS-001 PASS；r2 生成前语料质量 PASS。** 两项新提示已明确要求版本字段及版本列表元素使用 JSON 字符串，约束证据同步。相同正确调用下，字符串答案符合要求，数字答案违反明确类型要求。建议 S1 按原问题 ID 关闭并将连续未通过计数归零，保留首次 REQUEST_CHANGES 历史。

独立审核者为 Q1 AI。授权提交 `5dd1dc0a348b370c444d29ed28fb3fa40164362c`，D1 候选 `76e114fcecf60a92d03580283549cc4009f83df3`；范围见[复审任务](../../coordination/tasks/P05_G4_CORPUS_Q1_R2.md)。本结论支持按新身份冻结这 20 条任务，用于 [G4 协议](../../coordination/tasks/P05_G4_PROTOCOL.md)约束的真实候选生成；R1 技术验收、具体运行配置与 GPU 放行仍由 S1 协调。

## 定点修订与身份核对

独立比较完整新旧 authoring，确认仅两项 prompt 和对应 `constraints.evidence` 共四处改变；全部 20 项的答案、合法策略、脚本、faults、family 和 category 不变。两项原有的 2 条和 6 条合法策略继续成立。原 [r1 审阅](P05_G4_CORPUS_Q1_R1.md)的分母 20、18 PASS / 2 REQUEST_CHANGES 及原反例均保留；本轮定点接纳两项修订，复用其余 18 项逐条语义结论。

| 原序号 → 新序号，均按 1 起算 | 新任务对象 canonical SHA256 |
|---|---|
| 10 → 5 | `a9739fc435521cd1fc1e9ad1f2f0822d9c837244d1c035e1aa533e995ef05b14` |
| 13 → 11 | `c268e67881a67b1ef16bb21b70397d0429da8ec800df382e14646d4033106b55` |

全 20 项均完成独立 source hash/task ID 重算、对象差异及位置映射核对：2 个 task ID 改变，排序使 9 项位置改变；group hash 随组内身份改变，20 个任务对象的三处 group 引用一致更新。未受影响的 18 项除这三处引用外完全相同，不能称整个任务对象字节不变。新 group 为 `ec8b545e826c4f5e85f78dd5ea7237d37f081f2203f50a6b9ec471d673fd9177`。

新旧 group audit 经身份映射后完全一致，包括 200 条 P03 共享工具/schema 关系和全部任务处置。P02 四 split 元数据绑定及冻结 v3 的继承关系保持；两项新 source/template 键与冻结 assignments 没有交叉。全部 6 个暴露工具/schema 未变，复用 r1 全量分组检查：20 条仍为 1 个 train 连通组，隔离 0。P03 原身份保持，同组未来评测仍为 seen-group 诊断。未读取 held-out prompt/答案。

## 实际验证及证据

D1 索引绑定的 34 份文件及 S1 接收证据全部核对通过。独立回读四条既有合成 CPU 轨迹和八份实际请求，将新提示、逐轮完整 ModelInput hash、oracle payload、工具 registry、原始动作及进程回收记录逐一绑定；使用未改变的确定性 oracle 重评分，得到 **2 success / 2 failure**。每对轨迹的完整输入和工具调用相同，最终答案仅有版本值的字符串/数字表示差异；数字反例与 r1 原反例一致，现在失败有明确提示依据。

Q1 本轮新增轨迹 **0**，未重跑原 52 条 CPU 轨迹。实际检查命令为下列一条，exit 0；`Q1_PRIVATE` 是交接消息中的私有证据目录，`PYTHON` 是既有 Python 3.14.7 环境，从审核 worktree 根目录运行：

```sh
PYTHONPATH=src "$PYTHON" "$Q1_PRIVATE/review_r2.py"
```

| 输入或私有证据 | SHA256 |
|---|---|
| D1 evidence-index.json | `b2b9e9801ba8c5f4455b845c43f3d2e72df636bdc715eebde3d5c960b105aee7` |
| S1 接收证据 | `b2a79decddcd618c02509670a104844b5d495f480c2dc8bdeaa93a13adbf5e7b` |
| 新 tasks.json 文件 | `b9c6f18995579d8af1a58d137cafe9cc1c9f2f40279d9434aa85e2c7769eb015` |
| 新任务包 canonical hash | `4c9e7edaef35352a294aa8d62130847264645059dd5ce529fb528f926c339bd8` |
| 新 package manifest | `e7ab7b10728513662ddf3521e2c4b73b83eee7c7d50af31b469539a5f9d0427c` |
| Q1 evidence-index.json | `a89e7f2065d1c6e8472b9c58a2725b28265e65d54cd3271b11363744e0fec336` |
| Q1 review-result.json | `0bcff9d3bd7c6eca65cdff77dc9c6edf599637d84d1b8d0e8b8ee07db327db00` |

真实模型候选与正式偏好均为 **NOT_RUN**，本轮不计算偏好误标率。后续仍须检查真实 decision_inputs 中的 observation 依赖、首分歧语义与 unknown/tie 处置，并实际执行冻结偏好池的 Q1 审核及严格大于 5% 规则。四条合成轨迹不登记为正式偏好。公开变更仅本报告和[交接](../../coordination/handoffs/P05-g4-corpus-q1-r2.md)，原材料和全部逐项证据留私有目录。
