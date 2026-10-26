# P06 G5 隔离参考 CPU r2 交接

原48题已整组隔离，retained=0、quarantined=48；原记录保持。完整参考已包括P02全部split metadata、P03十题、G4二十题及原G5四十八题，保留完整工具声明、分组键、851条历史边和全部组件成员。详见[本轮报告](../../reports/P06_G5_QUARANTINE_REFERENCE_CPU_R2.md)。

- 基线：`1f9f8fc0270a1c1be022c90c1591716daabfa42d`；实现：`2153c6823ed98db58782037acba7ca348e4010ed`。
- 公开实现仅变更 `src/toolalign/data/evaluation/audit.py` 和对应原创测试。新增显式历史G5参数；原调用审计与Q1原文件逐字节一致。
- 13项定点测试及真实参考回读通过。原创CPU节点从无历史时保留1变为加载历史后保留0，并连接全部78个旧节点。函数/catalog改名后的schema及normalized-schema隔离检查通过。
- 原D1/Q1证据和输入共391份文件hash/长度不变；99条轨迹、tokenizer矩阵、模型均未重跑。
- 私有根：`.toolalign-local/p06-g5-quarantine-reference-r2/`。读取入口 `reference-manifest.json`、`reference.json`；recipe为 `prepare_inputs.py`、`build_reference.py`；全量交付以 `evidence-index.json` 绑定。报告提供可直接使用的读取代码。
- 完整参考SHA256：`9e24be0903bd821fc63b38018eb22c988c176caa28b5185d4948fcf3e56e5f44`；参考manifest：`6ae740f9be378de15826b3af31dbd8ad6b27e64cd37b34f12afb14b73209fcc5`。

等待R1/Q1复核及S1接纳。未恢复、修补或构造正式L1题；Q1-G5-CORPUS-002不在此宣布关闭。新旧语义连接仍需实际程序证据；原组件不能通过删除桥接题或改名恢复。
