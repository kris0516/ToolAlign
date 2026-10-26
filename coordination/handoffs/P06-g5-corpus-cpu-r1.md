# P06-g5-corpus-cpu-r1 交接

2026-10-27，D1；状态为 `READY_FOR_REVIEW`。实现提交 `72b18ad9c47da4932857cb53400b6a3c9ead6aad`，基线 `beb26eeebefd6f2a42d678e661e6175d0708f003`，分支 `codex/d1-p06-g5-corpus-r1`。交付 HEAD 在最终回报及私有 evidence index 中登记；本交接文件与报告只补充已运行证据，不改变实现。

结果为 48 题、23 family、1 个真实连通组，四域各 12、六类各 8、恢复题 8。分组和长度均未隔离题目；1 组不满足冻结协议的区间和 leave-one-group-out 计算条件。51 条正向、48 条反例全部符合预期，199 个 owned child 全部回收；22 项原创定点 CPU 测试通过。固定 tokenizer 最大历史输入 1,340，加 256 预留为 1,596；A2 四组共 12 个开发 ModelInput，最长 1,299 tokens。

新增文件只在 `src/toolalign/data/evaluation/`、`tests/data/evaluation/`、本交接和[公开报告](../../reports/P06_G5_CORPUS_CPU_R1.md)。旧 G4 reader/任务、P02 分组、工具目录、T1 后端/harness、contracts 和依赖锁不变。独立工具依赖已由 S1 接纳；当前语料的 R1/Q1 审核仍待进行。

| 核验 | 结果 |
|---|---|
| source/tool/schema/normalized-schema/family/template 闭包 | 纳入 P02 11,300 条、3,517 组，P03 10 题，G4 r2 20 题；新组件无旧节点 |
| 可读题近重复 | 2,568 对；阈值 0.85；新旧最大 Jaccard 0.09375 |
| 作者语义材料 | 48 题、23 family 的差异与共同机制均记录；跨域只读拒绝 family 明确连接四域；待 Q1 |
| 真实 CPU 执行 | 51 正向、48 反例；8 次 transient、8 次真实超时观察；没有 mock 工具输出充作证明 |
| 多步历史 | 10 条正向脚本的第二请求含第一真实观察，依赖 ID/计数匹配 |
| T1 输入消费 | S1 指定的在研 reader 源码快照读取 L1/A2 通过，计划为 104 / 8 个单元；待最终 T1 版本组合绑定 |
| 发布边界 | ruff、契约冻结、公开内容检查通过；原始题目、答案、轨迹均私有 |

最终 L1 tasks SHA 为 `10a842b4a0c2d15470ba9d61e010621a8dc0807ce5a9e4c0cc552b994b67d70e`，package manifest SHA 为 `5a4c0bc5cbaf0adbe4ddc708367fbfbbeda3f520c2b3b210cdcea9c1103b96c0`，A2 inputs SHA 为 `ec282f4779deca1815af39e2c68c846e831c184965318f3550eeaff973d03166`。共享 consumer 格式与复现入口详见报告，私有根/evidence-index 由 S1 本机映射消费。

原失败保留：首次静态检查的 import 分组错误，以及作者 helper 把 raw answer 传给要求 answer record 的脚本函数；分别修正后静态检查和实际 99 条轨迹通过。未加载固定模型，未下载或安装依赖，未生成偏好、训练或使用 GPU；正式模型评测、缓存性能与模型成功率均为 `NOT_RUN`。

R1 审核构造/隔离/消费接口；Q1 在正式运行前独立审阅全部保留题目的语义、允许和错误策略及分组。S1 负责最终 reader 绑定、集成、输入冻结和资源授权。
