# P06-g5-tools-cpu-r1 交接

E1完成[8个只读工具及固定catalog选择](../../reports/P06_G5_TOOLS_CPU_R1.md)，**本地109项工具检查通过，待R1独立技术审查及S1接纳**。授权起点 `b39d20d2d4f7ea87ff1f60bf7f4c9e10976d6d00`，分支 `codex/e1-p06-g5-tools-r1`；已采用S1接口补充 `34f841d72cf3f570486779590dfe542ee09a53d4`，未合入该文档提交。精确交付commit与完整命令回执见私有 `.toolalign-local/p06-g5-tools-r1/evidence-index.json`。

T1集成接口为 `LocalToolRegistry(names=None, *, catalog_id="local-devops.v1")` 和只读 `registry.catalog_id`；选择新集时传 `catalog_id="heldout-devops.v1"`，并传入需要advertise的工具名subset。通过 `registry.tools` 取得完整schema，`registry.manifest` / `registry.registry_hash` 绑定选择结果。LocalToolExecutor会在owned child重建同一catalog/subset并核对hash。CLI默认、旧工具源码/spec/manifest/hash保持。

D1资源入口为 `src/toolalign/tools/heldout_catalog.py`，`DOMAIN_TOOLS` 给出四域的有序工具对：

| 域 | 第一步 | 第二步 | 返回值依赖 |
|---|---|---|---|
| releases | read_release_manifest | read_deployment_snapshot | deployment_id |
| incidents | summarize_incident_window | assess_incident_policy | policy_id、event_count、critical_count |
| packages | inspect_package_build | assess_test_suite | suite_id |
| storage | inspect_storage_pool | assess_quota_allocation | quota_id |

完整参数边界、资源差异、语义错误及4个已实际执行的两步示例见报告。组件示例未生成最终48题或隐藏oracle；四域的真实连通group数需D1用P02/P03/G4 source/tool/schema/template键独立审计。

验证沿用既有轻量CPU环境：新增52项、原回归57项，共109 passed / 9.90秒，Ruff通过。覆盖全部8工具、subset/一次性调用、错误catalog/source绑定、参数及资源语义、故障注入、真实超时/取消和回收。源码hash、旧默认身份逐字节对照、实际输入/输出、process records及分发/公开内容/冻结契约检查回执均纳入私有索引。

范围限registry、executor、新catalog、新tools测试及报告/交接共6文件；T1的model_io/eval/harness/runner/Colab代码、依赖、contracts、旧数据与共享状态未改。本轮没有更改项目依赖或现有环境、下载模型、操作GPU/Colab或读取最终benchmark答案；分发检查使用离线构建。请S1回读提交及索引后交R1技术审查，再安排T1集成与D1私有任务构造；正式模型效果不由本CPU交付推定。
