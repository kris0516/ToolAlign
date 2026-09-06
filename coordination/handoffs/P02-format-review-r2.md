# P02-format-review-r2｜独立复审交接

**PASS；P0=0 / P1=0 / P2=0。原 F1/P2 已关闭，原 7bada 的 FAIL/P2=1 保持。** R1，2026-09-06，gpt-6-astra / max。

授权 `41233633ac9aeaf72e66b280908bc0156149c0f2`；本轮分支 `review/p02-format-r2`；唯一被审 candidate `8c439f683b9d6b04919ff1f7184d8924ccf82f9f`，parent `6c82d29ddaade349d3e2a15f50d35214dbc7bf8d`，tree `0695bd9605148be3304ba8824506098bdfa9bc46`。本轮 review 完整 SHA 在原生交接中提供，其唯一父提交为该 candidate。

已核对 b4dc1cf 仅改 offline.py / 新增 test_snapshot.py，7b8ef31 先保存证据，6c82d29 普通 merge 原公开 2942e568，最终 8c 仅更新三份 D1 报告。原 234 文件与 12 份原 review 保持；本轮 251 份候选字节保持。原本地 f708 及所有原分支/私有记录保留，f708 不在候选和新 review 的公开祖先。未合随后 main/P01，未修候选或修改其他 worktree。

- **真实 before/after：** D1 原 before 与原 R1 source/默认 wheel 结果完全相等，reference FAIL（声明相同、`!` 0→30），native PASS。新精确源码和本轮默认 wheel 实际安装 target 均通过未改原 snapshot 探针；reference 实际 backend 与原正常基线相同、`!` 为 0。源码/安装 reference 结果 SHA 同为 `a5672aeb79df254d9bb91651cff88824a2700a07d22c262687d4b8d08814663c`。主反例未 mock loader、返回值、identity 或期望 hash。
- **邻例与自足：** 原 10 来源情形在两 engine 各通过；新增 7 种来源/资源情形为 native 4 次、reference 7 次执行。真实写入、HF JSON 与模板异常均清理；成功后删除原来源及临时快照，重复 render/encode/decode/sequence/parser 仍通过。同用户任意 OS 攻击隔离不是验收范围。
- **适用 pytest：** 原组合加新 native 为 675 passed / 2 HF-only skipped；原 R1 结构/统计另组 60 passed / 0 skipped，两组无重叠，共 735 passed / 2 skipped。真实 reference 的候选新测试另外 13 passed / 0 skipped，覆盖两个 HF-only cleanup，重叠项不重复累加。Ruff、四文件契约冻结和公开扫描通过；实际命令/log hashes 见证据索引与最终私有封存。
- **真实同 12 例：** 两 engine 完整 P/C/IDs/sequence/EOS/masks/shift 与原 R1 和 D1 普通 v1 记录相同。两个模型身份共享三文件，不称 24 个独立场景。native/reference 完整结果 SHA 分别仍为 `680986e8c0858d8838596f31dbb18683aef281668771c7180a6f750804db3a43` / `79fd96ef8f6d8d1d4fe454807218f3166fd54f2704becff1ef93056b2ae13e88`。
- **实际新包：** 精确 8c 新建 sdist/default wheel/显式重建 wheel，成员 88/44/44，39 份包源码/资源与 Git 匹配；10 条纯默认隔离安装/接口命令通过，仅六个默认 distributions，未加载可选 tokenizer/模型。两个实际安装 engine 的原反例逐模块验证七个 ToolAlign 模块来自 target；安装 reference 的清理后同 12 例另核对 14 模块。源码直接 wheel 为 NOT_RUN。
- **旧全量与人审：** 只读重核原两套各 18 制品、原 8,228 行/hash 及全量/分层统计；原 native b33a55f 与原 R1 reference 7bada/时间/环境分别保持，承认 offline.py 已变化。正常新小集相同，本轮全量重新编码为 0，旧 manifest 未改。100 来源/114 决策人审材料和填写副本仍保持、0 reviewer/0 verdict，没有代签。

R1 复用既有 native tokenizers0.22.2 与 reference Transformers5.16.1/tokenizers0.23.2/Jinja3.1.6 环境。R1 reference fsspec2025.3.0 与 D1 reference2026.7.0 分别登记，未新建 tokenizer 环境或联网下载。导入前离线、禁用 Torch/TF/Flax，实际断言无模型模块。新增私有制品与本轮明确测试目录的容量封存低于 2GiB；保留容量与临时累计 I/O 的区别见报告。

完整结果、范围、逐项旧审查映射、归档 hashes、失败/NOT_RUN 见[复审报告](../../reports/review/P02-format-r2/README.md)与[证据索引](../../reports/review/P02-format-r2/evidence.json)。D1 620/37、542/39 和原 R1 37/42 的制品/命令身份分别重新核验，旧真实失败与开发失败未覆盖。本轮登记验证没有非零退出。公开路径只用角色占位符，实际命令和原始日志留私有；最终历史载荷扫描与 commit/clean 读回由原生交接补充。

仅新增 `reports/review/P02-format-r2/` 和本交接单。R1 不 push、不合并 main、不改协调状态，不进入其他任务。PASS 不等于 G-DATA、模型质量或 P04 验收；S0 最终集成/CI/main 验证与 kris 人审仍待完成。提交新的独立 review 后结束本轮。
