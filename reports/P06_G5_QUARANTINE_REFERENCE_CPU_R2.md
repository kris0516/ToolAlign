# P06 G5 原48题隔离与完整排除参考 CPU r2

**已落实 retained=0、quarantined=48，并冻结可供后续候选读取的完整排除参考。** 原48题保持原记录；加入Q1有据语义桥后，重算审计与Q1保存的审计文件逐字节相同。一个原创CPU图节点接入历史G5后，连接到原48个G5、20个G4、10个P03节点组成的组件并被隔离。新候选尚未构造，本包等待R1/Q1复核，不宣告Q1-G5-CORPUS-002关闭。

范围依据[任务书](../coordination/tasks/P06_G5_QUARANTINE_REFERENCE_CPU_R2.md)、[Q1正式r1](reviews/P06_G5_CORPUS_Q1_R1.md)和[后续候选边界](../coordination/tasks/P06_G5_L1_REPLACEMENT_PLAN_R2.md)。基线为 `1f9f8fc0270a1c1be022c90c1591716daabfa42d`，实现为 `2153c6823ed98db58782037acba7ca348e4010ed`；Q1来源为已接纳的 `08d4c5a`。原r1的误判证据、答案、脚本、轨迹和失败记录保留。

| 排除参考 | 已冻结内容 |
|---|---|
| P02 policy-a | 11,300条metadata、3,517个原group；train 10,033、validation 411、test 381、ood_test 475。保留原assignments、完整tool-lineage声明及派生normalized-schema键；未读取保留测试题面或答案。 |
| P03 | 全部10个公开开发任务及其完整工具声明。 |
| G4 | 已接纳r2的全部20个train任务、原family/group和工具/schema/source/template身份。 |
| 原G5 | 全部48题、23个family、8个工具的完整声明及全部分组键；原记录和原group身份保持。 |
| 图与审核依据 | 3,595个节点、3,506个参考组件，含原G5连接的78节点组件。1,753条边记录由902条重算键连接及851条保留历史依据组成；后者包含7条近重复边和1条Q1语义边。 |

参考组件包括所有P02旧组，即使其没有连接原48题也保留。P02每条metadata到原group的对应关系、原G5整组件成员及连接理由均可回读。历史图角色前缀从 `new:` 显式映射到 `g5:`，原task ID、family、工具/schema键和记录内容不变。

[audit.py](../src/toolalign/data/evaluation/audit.py)新增可选 `historical_g5_reference`，读取原始 `tasks` 及带既有节点端点的 `edges`，恢复旧组件中的语义和近重复连接，并输出完整参考图。未传入该参数时保持原行为。未修改旧oracle、contracts、工具、后端、依赖或共享状态。

13项分组定点测试通过，另外14项不受影响测试未重跑。检查覆盖全部P02 split的传递隔离、跨域family、近重复和语义连接、完整旧组件保留、历史边端点约束，以及函数/catalog改名后schema和normalized-schema仍触发隔离。真实参考回读探针在不加载历史G5时保留1个CPU节点，加载后保留0，并保留全部78个旧组件成员。该节点仅为图接口fixture，未作为正式L1题，也未执行脚本或工具。

实际读取原D1索引的177份文件和Q1索引的203份文件，连同原输入共391份受保护文件，构造前后hash及长度全部保持。未重跑99条轨迹、tokenizer矩阵或模型；无GPU、依赖安装或模型下载。

私有交付目录为 `.toolalign-local/p06-g5-quarantine-reference-r2/`。`reference.json` 保存完整读取参数、原记录、图和来源；`inputs/p02/tool-lineage.jsonl` 保存完整P02工具声明，路径及hash已绑定。`disposition.json` 保存原48条记录与新隔离处置，`retained-tasks.json` 为空，`group-audit.json` 保持Q1审计原字节。`reference-manifest.json` 绑定这些文件和全部输入快照，`evidence-index.json` 另绑定recipe、检查和最终交付身份。

后续工具/语料任务可按下列方式读取。新增语义连接使用 `new:<task_id>` 与 `g5:<原task_id>` 等节点身份；已有Q1连接通过历史边自动恢复。新旧语义等价仍须作者和Q1按实际程序提供证据，词法与schema检测不表示语义检索完备。

```python
from pathlib import Path
from toolalign.data.common import read_json, verified_build_manifest
from toolalign.data.evaluation.audit import audit_groups

root = Path(".toolalign-local/p06-g5-quarantine-reference-r2")
verified_build_manifest(root / "reference-manifest.json")
reference = read_json(root / "reference.json")
retained, audit = audit_groups(
    candidate, reference["p02_rows"], reference["development_cases"],
    reference["g4_bundle"],
    historical_g5_reference=reference["historical_g5_reference"],
    semantic_links=new_semantic_links,
)
```

| 文件 | SHA256 |
|---|---|
| 原G5 tasks，保持原字节 | `10a842b4a0c2d15470ba9d61e010621a8dc0807ce5a9e4c0cc552b994b67d70e` |
| 重算group-audit，与Q1逐字节一致 | `bdaaca3c3af06d5fc57abe8887842742fb2470ec1f0cb789e435345739be7852` |
| 完整reference.json | `9e24be0903bd821fc63b38018eb22c988c176caa28b5185d4948fcf3e56e5f44` |
| reference-manifest.json | `6ae740f9be378de15826b3af31dbd8ad6b27e64cd37b34f12afb14b73209fcc5` |

完整排除参考及隔离处置已由本轮CPU证据支持；正式接纳和问题关闭由R1/Q1复核后交S1决定。后续候选资格和模型效果均未在本轮评估。
