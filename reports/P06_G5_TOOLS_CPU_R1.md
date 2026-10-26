# P06 G5 只读工具集 CPU 首包 r1

2026-10-26；E1。**8个新工具与固定catalog选择已实现，本地109项工具检查通过，待R1独立技术审查。** 四个工作域均用真实owned child完成两步调用，第二步读取第一步返回的标识；旧六工具的源码、schema和默认manifest身份保持。T1可通过固定API选择catalog及advertised subset，D1可据下列资源语义构造私有测试。

授权起点 `b39d20d2d4f7ea87ff1f60bf7f4c9e10976d6d00`，分支 `codex/e1-p06-g5-tools-r1`，执行[工具任务](../coordination/tasks/P06_G5_TOOLS_CPU.md)及[G5协议](../coordination/tasks/P06_G5_PROTOCOL.md)。另已读取并采用S1接口补充 `34f841d72cf3f570486779590dfe542ee09a53d4`；该文档提交未合入本分支。

## 固定接口与执行绑定

```python
from toolalign.tools import LocalToolExecutor, LocalToolRegistry, heldout_catalog

registry = LocalToolRegistry(
    heldout_catalog.DOMAIN_TOOLS["releases"],
    catalog_id="heldout-devops.v1",
)
executor = LocalToolExecutor(registry)
advertised_tools = registry.tools
```

构造签名为 `LocalToolRegistry(names=None, *, catalog_id="local-devops.v1")`；`registry.catalog_id` 为只读property。仅接受 `local-devops.v1` 和 `heldout-devops.v1`，未知ID、模块路径或callable明确拒绝。`names=None` 选择该catalog全部工具；传入名称只选择其中subset，不能跨catalog混入工具。`heldout_catalog.DOMAIN_TOOLS` 的键为 `releases`、`incidents`、`packages`、`storage`，每个值依次为第一、第二工具名。

`registry.tools` 提供完整可序列化spec，`registry.manifest` 提供schema/source/implementation绑定，均返回副本。manifest结构仍为 `registry_version` 与 `tools`；新工具implementation为 `toolalign.tools.heldout_catalog:<工具名>`，source_hash取实际 `heldout_catalog.py` 字节。现有CLI维持默认旧catalog；新catalog由上述Python API选择。

父进程将catalog ID、所选名称和registry_hash传给owned child。child用固定模块表重建同一subset并核对hash，成功后才记录执行标记、调用该registry绑定实现。错误catalog、跨catalog名称或不匹配hash返回 `rejected/child_binding_mismatch`。一次性ValidatedCall、参数白名单、故障队列、时限、取消与进程回收路径保持。所有新工具为 `read_only`，单工具上限1000ms；没有caller路径、网络、环境或训练数据读取。

## Schema和固定资源

下表参数均必填，禁止额外字段；数值均为有上下界的integer，字符串为enum。ID的完整枚举见[固定资源源码](../src/toolalign/tools/heldout_catalog.py)和 `registry.tools`。

| 域 / 工具 | 参数 | 资源与返回语义 |
|---|---|---|
| releases / `read_release_manifest` | `application`: comet-gateway / lattice-worker；`release`: 4.2.0 / 4.3.0 | 4份计划清单，返回deployment_id、artifact_label、desired_replicas、channel |
| releases / `read_deployment_snapshot` | `deployment_id`: comet-blue / comet-green / lattice-blue / lattice-green；`snapshot_day`: 2026-10-12 / 13 / 14 | 4个部署各有12、13日的实况；返回实际running_release、ready_replicas、state；14日无记录并报错 |
| incidents / `summarize_incident_window` | `route`: parcel-ingest / replica-sync；`day`: 2026-10-18 / 19；`start_minute`: 0–1439；`end_minute`: 1–1440 | 4个route/day窗口共13条固定事件；UTC分钟，起点包含、终点不包含；返回events、event_count、critical_count和当日policy_id |
| incidents / `assess_incident_policy` | `policy_id`: parcel-rule-1 / 2、replica-rule-1 / 2；`event_count` / `critical_count`: 各0–100 | 4条固定规则；任一计数达到相应阈值即建议page，否则observe；返回recipient但不发出通知 |
| packages / `inspect_package_build` | `package`: cedar-cli / drift-agent；`version`: 2.4.0 / 2.5.0；`platform`: linux-amd64 / linux-arm64 | 6份构建记录，返回build_id和suite_id；两个包的2.4.0 arm64组合均无记录 |
| packages / `assess_test_suite` | `suite_id`: 固定6项；`required_cases`: 长度1–4的数组，每项为install / upgrade / rollback / healthcheck | 读取pass、fail或not_recorded；保留请求顺序及重复项；全部请求项均pass才令all_passed=true；不实际构建或运行测试 |
| storage / `inspect_storage_pool` | `pool`: archive-tier / scratch-tier；`tenant`: finch / oryx；`snapshot_day`: 2026-10-20 / 21 | 2个池的物理capacity_gib/free_gib及8个tenant/pool/day对应quota_id；物理可用空间与租户配额分别返回 |
| storage / `assess_quota_allocation` | `quota_id`: 固定8项；`request_gib`: 0–128；`request_objects`: 0–4096 | quota_id绑定租户、池、日期和版本；两维请求后用量均不超过各自上限才quota_allows=true；返回剩余额度，不分配存储 |

计划清单的release不保证该日实际部署已完成；同一部署两日实况可能不同。事件窗口的起点不得大于或等于终点，critical_count不得超过event_count。规则版本、软件包版本/平台、租户/池/日期均有不同的固定资源，调用者不能用相近对象替代。配额超过上限时remaining字段可为负，quota_allows为false；该字段只判断配额，物理空间需要读取池的free_gib。

通过schema但资源或组合不成立的调用返回非retryable工具错误：`deployment_snapshot_missing`、`invalid_incident_window`、`inconsistent_incident_counts`、`package_build_missing`。未知枚举、缺参、额外字段、越界、错误类型则在启动child前被拒绝。

## 已执行的两步组件示例

以下每行实际启动2个owned child，均completed、已回收且临时目录清除。第二步的关联标识取自第一步output；其余参数取自请求示例。这些是组件示例，不是最终评测题目或隐藏oracle。

| 工作域 | 第一步输入及结果 | 第二步输入及结果 |
|---|---|---|
| releases | comet-gateway / 4.3.0 → deployment_id=comet-green，desired_replicas=6 | comet-green / 2026-10-12 → running_release=4.2.0、ready_replicas=2、state=rolling |
| incidents | parcel-ingest / 2026-10-18 / [60,90) → policy_id=parcel-rule-1、event_count=2、critical_count=1 | 使用上述ID和计数 → recommendation=page、recipient=parcel-primary |
| packages | cedar-cli / 2.5.0 / linux-amd64 → suite_id=cedar-suite-25 | 此suite_id、required_cases=[install,upgrade] → pass/fail，all_passed=false |
| storage | archive-tier / finch / 2026-10-21 → quota_id=finch-archive-r2、free_gib=80 | 此quota_id、request_gib=20、request_objects=560 → 请求后64GiB/1000对象，恰好两维上限，quota_allows=true |

## 身份与验证

实现前保存了旧catalog字节、canonical manifest/spec字节及默认、6个单工具subset和空subset的hash；实现后逐项匹配。新catalog manifest绑定本轮实际源码，身份如下。

| 身份 | SHA256 / registry_hash |
|---|---|
| 旧catalog.py源码 | `8c89c7f2b4a4bc64952791b66954542cf328f814b07a9ba1c3f3e70b5e236792` |
| 旧完整registry与canonical manifest | `6cf0ff5e0b775068ddd9690e66414eee97725865d520e8df37072bc53d4085b8` |
| 旧canonical tools | `bbb7b2de3f520880764e7600c7361e757dcdb418c48fd3da50bf78e004164ced` |
| 新heldout_catalog.py源码 | `a13735a3cfd1ec5d3f638504d01d500438248d8efe545c97be085999b2046996` |
| 新完整registry | `66d47196bd207542325c89244a7fbafd2163f14c01e9aeb36e40553e01c7f037` |

沿用既有 `.venv`：Python3.14.7、pytest9.0.2、jsonschema4.26.0。`tests/tools` 共 **109 passed / 9.90秒，exit 0**，其中新增52项、原工具回归57项，无失败或跳过。验证包括上述8次实际执行、对象/版本/平台/日期反例、窗口边界与规则阈值、未记录测试结果、两维配额与无资源写入、缺参/非法参数拒绝、advertised subset、一次性调用、错误catalog/source绑定、transient故障后的新调用、真实超时/取消及回收。3个child绑定反例实际重建registry后拒绝，执行标记均未产生。

实际行为检查命令为：

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest -q tests/tools --basetemp .toolalign-local/p06-g5-tools-r1/pytest-004 --junitxml .toolalign-local/p06-g5-tools-r1/pytest-004.xml
.venv/bin/ruff check src/toolalign/tools/heldout_catalog.py src/toolalign/tools/registry.py src/toolalign/tools/executor.py tests/tools/test_heldout_catalog.py
```

Ruff exit 0。私有 `.toolalign-local/p06-g5-tools-r1/evidence-index.json` 汇总精确提交、受检文件hash、所有记录命令的argv/退出码、原始stdout/stderr、JUnit、4组实际输入/输出及进程证据、3个child绑定反例，以及公开内容、冻结契约和分发检查回执。没有重跑无关ML矩阵。

本包改动为registry、executor、新catalog、新tools测试及本报告/交接共6文件。旧catalog、contracts、任务/oracle、依赖锁、模型和共享状态均未改。没有更改项目依赖或现有环境、下载模型、操作GPU/Colab或读取最终benchmark答案；分发检查使用离线构建。四个工作域不代表四个独立连通group；D1后续须对真实P02/P03/G4键做隔离审计并独立构造私有L1任务，实际分组以该审计为准。正式模型评测仍NOT_RUN，本轮结果支持CPU工具实现与绑定。
