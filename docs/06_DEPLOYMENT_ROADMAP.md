# 06｜前瞻性部署路线：本地实验到受控服务

这是能力路线，不是全部立即实施的承诺。公开仓库 ≠ 公开在线 API；发布 Markdown ≠ 推理服务已部署。

## 1. 总体部署分层

```text
GitHub public repository
    └─ source, specs, small lawful fixtures, sanitized reports

Mac development/training host（private）
    ├─ immutable model cache / dataset cache
    ├─ one GPU lease shared by training & serving
    ├─ run artifacts / reference cache / checkpoints
    └─ native MLX worker

Local service（default 127.0.0.1）
    ├─ authentication and request contracts
    ├─ bounded queue, cancellation, deadline, rate limit
    ├─ model backend adapter
    └─ read-only registered tool runner

Optional later
    ├─ private VPN access by explicitly authorized client
    ├─ approved model adapter publication with licenses
    └─ separate Linux/CUDA backend, not Metal-in-Docker
```

## 2. 阶段及进入条件

| 阶段 | 相对时间目标 | 交付 | 进入/退出门 |
|---|---|---|---|
| plan-v0.1 | 当前 | Markdown 方案、独立对话协议、任务包 | 文档一致性检查；无实现完成声明 |
| v0.1.0-core | 十天内优先完成 | 数据、baseline、SFT、可执行评测、资源记录 | G-DATA/G-TRAIN/G-EVAL；全部局限公开 |
| v0.2.0-preference | 十天目标，兼容性不足则顺延 | DPO、有效 preference、同条件对照 | reference 与梯度验证；负结果允许 |
| v0.3.0-serving | 后续 2–4 周窗口 | 本地 API、cache、受控负载、回滚 | 服务正确性/隔离/取消验证 |
| v0.4.0-portability | 后续 1–2 月窗口 | 可选 CUDA/TRL adapter、标准导出与格式核验 | 至少一次真实跨 backend 对照，而不是仅写配置 |
| v0.5.0-domain | 后续 2–3 月窗口 | 未见工具/领域评测、可选 LiDARFoodAgent shadow 集成 | 新域测试集、隐私与契约审查 |
| v1.0.0-research | 后续 3–6 月窗口 | 多 seed 结果、稳定制品规范、可复现研究版本 | 独立复现、已知风险、发布/维护策略 |

时间窗口用于顺序规划，不是对外 SLA。不能因为日历到了就跳过质量门。

## 3. 本地 serving 第一版

建议一个轻量 FastAPI 控制层，一个原生 MLX 推理进程，一个受限工具进程；首版用简单持久化/文件 manifest，未出现明确并发需求前不引入 Redis/Kafka/Kubernetes。

接口建议：`GET /healthz`（存活）、`GET /readyz`（模型已加载且资源可用）、`GET /v1/model-info`、`POST /v1/tool-decisions`、`GET /v1/runs/{id}`、取消操作。所有接口是 P07 待实现契约，不是现有功能。

`tool-decisions` 返回结构化建议和可核验 trace ID，不直接给任意机器执行权。控制层验证输入长度、工具 allowlist、最大 token、deadline、幂等 key 与 payload hash。

默认仅 loopback。多终端访问先用私有网络/VPN，并增加认证、授权和日志去敏；不默认 `0.0.0.0`，不配置公开穿透。不把兼容某 API 格式与达到该提供商安全/服务等级混为一谈。

## 4. 版本化制品

模型制品身份至少包含：基础模型 revision、tokenizer/template、量化配置、adapter hash、训练 config、数据 manifest、代码 commit、评测协议、eval result hash、backend requirements。

以不可变 ID 载入制品。`candidate`/`stable` 是指向不可变 ID 的小型指针；切换前运行 smoke，切换失败恢复旧指针。不能覆盖旧模型文件后再说“可回滚”。

保留一个上一稳定版本；清理策略依据磁盘预算，只删除明确可再生的 cache，不删除对应实验的配置/指标/摘要。

## 5. 质量与服务门分开

模型晋级：数据来源审查、语义成功率、错误类别、无需工具误调用、安全约束，以及与旧版本的配对差异。

服务晋级：冷启动、连续请求、队列、公平性、取消、超时、OOM、加载失败、缓存失效、鉴权/越权、日志泄漏。首个负载实验用固定长短混合请求；一次吞吐高不代表长期稳定。

相同用户重试不应重复执行未来副作用工具。跨用户 key、cache、日志和制品授权边界必须测试。尚未做这些测试时，不称多租户生产服务。

## 6. CI/CD 策略

公共 Linux CI：静态检查、纯 CPU 数学参考、schema/data fixtures、oracle、parser/security 和文档链接。模型训练与 large download 不在每次 PR 自动运行。

Mac 验证：由用户认可的代码 commit 在本机独立运行，回填摘要和 artifact hash。即使未来配置 self-hosted runner，也不执行不可信 fork PR，不向测试开放真实凭据或家庭网络。

依赖升级先建分支，固定版本执行最小回归矩阵；禁止正式实验使用浮动 `latest`。Release 附依赖清单与已知未运行环境，不因为 CI 绿色就宣称 Apple GPU 全部通过。

## 7. 与 LiDARFoodAgent 的长期衔接

第一阶段完全独立，不复制私有源码和健康数据。将来只通过重新设计的版本化 JSON 接口传入最小化、去敏证据，ToolAlign 只输出候选检索/工具决策。

先在合成/去敏任务上 shadow 模式运行，比较原方案与新策略；不改用户真实记录，不取代 Swift 端安全校验、营养计算、确认和提交权。接入后的效果单独测，不能把通用 tool benchmark 增益转写成健康结果改善。

若需要复用既有 AGPL 代码，先作许可与开源范围决策，不把其代码直接混入 MIT 工程。协议集成不自动证明免除其他来源义务。

## 8. 不优先做的“前沿功能”

GRPO/agentic RL 需有可靠 reward 与更丰富环境后另立研究问题；不能为追热点把十天 SFT/DPO 实验改成在线 RL。自动生成 Skills 需要离线候选、审查、版本化发布，而不是模型自己改生产代码。MCP、A2A、多 Agent 只有真实互操作需求才加入。

更大模型、多卡和云部署保留适配位置，但没有运行就写“设计支持/未验证”，不列入已完成技能证明。
