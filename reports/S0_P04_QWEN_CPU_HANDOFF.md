# P04 固定 Qwen CPU 包完整交接接收

完整候选 `01eeb74d1bce3c3a3c41d84575d4d706e246e818` 已由 E1 普通推送，原生任务 completed/idle，远端分支相同；状态 **READY_FOR_REVIEW_CPU**。[Draft PR17](https://github.com/kris0516/ToolAlign/pull/17)已建立。S0 完整接收通过，独立 R1 尚未开始此包，当前先审查 v3 数据适配器。

候选 tree `3b194325c9b6ecba4356f46eb4ad91c8f9e63642`；其直接父为源码提交 `207c24c486a562760c51b8de3193c3e78028ba6d`，源码提交直接承接已验证生产基线 `a2b595c39d84f4e3ba32ee5893f3fff8c9202f4d`。617 基线文件保持，新增六份为固定模型模块、原创测试、S0 原字节 metadata 配置、两报告和 handoff。最终三份文档不改变打包源码。

2026-09-07 19:48:44–19:48:48 UTC，S0 核验 **26,330 条当前文件路径**，证明 SHA `c8abe8953aab67664bfd9764633c176f508505e2cef09e2fd03f6222e279fff9`。候选623文件、scope21,912普通文件/282,866,494 bytes与1GiB预算、34份原命令及20,862份原源码快照均绑定；计数相互重叠，不累加为独立覆盖。

| 接收项 | 实際核验 |
|---|---|
| 终态 | seal `870dff7c757dc9603c0eba376eb9e59de298138340dfad9f194d3168b1d5b4ec`；FINAL_RECEIPT `0ff8efa67bf636c3b5e216f4c2c60795bbcb216fa4a9c7fed1e71b6a6c248b64`，19:35:04 UTC收尾 exit0 |
| 原始命令 | 34份 argv/cwd/UTC/exit/stdout/stderr、实际源码epoch和helper原字节；33独立字面量shell调用、1个已观察多行shell的最终命令；另核验封存回执命令真实退出 |
| 输入 | 固定42成员manifest `41aadaa79eac7467c7ef2b7c39a0524ec894d1b0e9c616d7a6ab303d05e33cc5`、配置 `b8a5e48bc2b93064c511ba796dabf55024f65df97fe0db39c43366b7bc877145` |
| 模型文件 | S0仅流式核对原字节hash与三个小header JSON；两模型合计622个BF16 tensor的名称/shape/dtype/offset与固定metadata相同，未解码tensor值、未复制权重 |
| source/installed | 原各一轮两模型20文件验证；各9个ToolAlign模块的实际路径/hash分别来自源码和新target；模型结果除原运行时间外一致，完整分项结果与总结果对应 |
| CPU自测 | E1最终120 passed/0 failed/0 skipped，执行时源码逐字对应207c24c；Ruff、4冻结契约和623路径公开扫描通过；仍为实现者自查 |
| 历史保全 | 4,376当前路径、498原Git/快照、1,209旧scope文件、39链接、3旧refs、根identity与196构建支持路径保持 |

实际 sdist 为401,044 bytes，SHA `73ee4795ca39d81021b3eed1eb1ed4b8a9e9d3caf5899469e91cfd75f5f7e1cf`，144成员中143份直接绑定候选Git字节。直接及sdist重建wheel均204,275 bytes、70成员，SHA `117f74f92aad166aceb16336771ec4d4bf9f98e7ac6142fb0592d2c1246373d6`；完整RECORD、65个包文件与新默认target一致。现有Hatchling/uv支持沿原授权复用，无新环境或依赖安装。

原生命令绑定证明 `18c114233d6a87eb515888315aef79b17436a32189a6f5a393babafac786d4f3`。完整日志文件直接核hash；工具只显示尾部时，不声称全日志均显示。原006 unused import、007测试错误前缀预期不符的非零记录保持；修正后最终120通过，不累加早期重复测试。S0接收脚本首次将异步收尾误按同步调用投影的失败保留，改为绑定原启动session及真实退出后通过；未重跑任何E1消费。

原source结果 `21512c5f0787b23a86c1f76c43f9c561717c0fb4869b6e53f9c4d90619d94ffd`、installed结果 `c4416f988c27a205dfc0279d0e293d8200a2893b9f1d5eddc2d8613277a319a2`；两条既有固定额度均用1/1。它们只证明文件与header验证；311序列化tensor、sanitize预期310底座叶、112个LoRA叶是分开的身份和预期，真实装配/参数内容测量没有发生。

E1早期四次pytest使用默认共享临时根的事实保持。旧R1的30文件/1链接原路径缺失按[S0保全记录](S0_P04_REVIEW_EVIDENCE_PREPARATION.md)继承，不把范围内保全写成全局临时目录未变；没有恢复或清理旧目录、没有重跑已成功测试。后续pytest使用新的任务独占basetemp。

[R1固定模型CPU审查](../coordination/tasks/P04_QWEN_MODEL_REVIEW.md)已准备精确候选，等待当前数据审查正式结束和原生终态后派发。最终CI/main及真实loader、零LoRA对照、容量、保存/重载、baseline/SFT/DPO/正式评测均未验收。本次S0新构建/安装、生产validation API、框架/模型/tokenizer/GPU均0；直接原字节/header检查单列，不称模型已加载或服务已上线。无需kris操作。
