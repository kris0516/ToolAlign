# P01｜S0 主分支集成与 G1 验收

2026-09-06；S0。**P01 VERIFIED；G1-SFT PASS，G1-DPO 的唯一备选路径 PASS。** 结论限定于已记录的本机兼容性、数学/身份检查及受限 smoke/容量校准。首选 mlx-tune DPO 仍 FAIL；正式 P04/P05 训练、最终 checkpoint 和真实完整 harness 尚未验收。

## 精确提交与独立复审

- [PR #6](https://github.com/kris0516/ToolAlign/pull/6)已读回 closed/merged，实际 main 合并为 `d10722e491d6a8efe26b8248efb9c19cc2216742`。
- 完整被审候选为 `9fe3cbe3a067725c37dc213bbf38f9c90ceb5066`；R1-r3 PASS，P0/P1/P2 均 0；原始 [review 7e20706](../coordination/handoffs/P01-review-r3.md) 为 `7e207060539df682691b4d149e68b7ab4ffc3175`，直接以完整候选为父，只新增 6 份审查文件，183 份候选文件未变。
- S0 完整读取新报告、13 场景原创探针、证据审计器和包核验器，实际核对 178 项文件/日志/结果/制品/归档 hash。证明 SHA-256 为 `badf039e7a08908e1457d2a5423df89ce1eb0d2c0401336b5c88e062ad189b56`。原 R2-F1 启动初始化问题关闭，原运行期、F2 已执行更新计数及 F3 历史源码映射的关闭结论保持。
- R1 原始 29 项反例与其余 251 项 CPU/报告检查通过；新增 13 个独立场景通过，共 293 个不同检查。安装后的同 13 场景属于重复验证，未再加计。两条最初遗漏 PYTHONPATH 的收集命令 exit=2 已保留，只改调用方式后通过，没有改反例或候选。
- S0 普通 merge 原 review 和当时 main，形成最终 head `90b29363b4d2ba8003ed7af17fa359960702b33c`；全部 214 个既有 main 路径与 61 个 P01 被审路径字节保持。原始 FAIL、模型负结果和所有父提交均保留。
- [最终 CI 34016103173](https://github.com/kris0516/ToolAlign/actions/runs/34016103173)的 Python 3.11/3.14 jobs `101440026903` / `101440027028` 所有步骤成功。实际 main 与最终 CI head 的 tree 均为 `ef6b103736dec05ee3984c1770e5bbcbe87616fd`。

## 实际 main 组合验证

2026-09-06 06:20–06:24 UTC，Python 3.14.7、macOS arm64、纯 CPU、离线。复用逐项核对的 28 包 CPU 环境与固定 tokenizer 输入；没有加载 MLX/Torch/模型。本报告的实测均绑定上述实际合并提交，随后 S0 状态文档不改写历史结果。

| 实际检查 | 退出码与范围 | 原始日志 SHA-256 |
|---|---|---|
| 完整 P01/P02/P03 与原 R1 组合 | 0；**655 passed，0 skipped**，45.22s | `ec385ea673a6c1dcb74a0556c3ce47987e1147276c1b2de04224dd61e3929716` |
| 固定 CPU 环境及 tokenizer 身份 | 0；28 包版本与原三个来源小文件一致 | `a81ba5e010efab34a22c09b3efdf852110fc07c7e461e30cd3d801c5c49b240d` |
| `uv run --offline --locked ruff check .` | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `scripts/check_contract_freeze.py` | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `scripts/check_public_content.py` | 0；275 个追踪路径 | `e4f9a7fb7d97878b017c243cba44caf6f098ea3c7945d615e3cbdac448cd1f38` |
| 实际 `uv build --offline` | 0；sdist 和由其生成的默认 wheel | `a2b5fe2b76239908644cd7ca1a55476dad7c78924b2d6aa1ae88e9c406cc157f` |
| 从实际 sdist 显式重建 wheel | 0 | `f988bd7f702889110ce293385f858c3cd5a1ba8fe73a221442fe812c89a27a6f` |
| 三份归档当前 Git 字节核对 | 0；无未追踪载荷/缺失或差异 | `3a635c3e39943e21b33191614b3a911af9978bb7b85f1da2b317e85d58e37804` |
| 新隔离安装与组合接口 | 0；21 条子命令全部通过 | `7719e95d836f7f1761ed72e1c6245d983bc25dde6530dd23b8f14f2f057a708e` |
| 新 demo 制品、共享锁及人审状态 | 0 | `94ff732cf2a12863381567efb48004f93a8ab9c49fbfddbf5ab246775935021a` |

655 = 已验证 P02/P03 组合的 551 项 + P01 新增 104 项，不重复累计原基础包或历史结果。完整命令如下；本机环境与临时目录取值在私有记录中绑定，basetemp 位于独立系统临时目录。

```bash
PYTHONPATH=src TOOLALIGN_TOKENIZER_DIR="$TOOLALIGN_TOKENIZER_DIR" "$S0_CPU_PYTHON" -m pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py reports/review/P02/test_p02_boundaries.py reports/review/P03/test_p03_lifecycle.py reports/review/P03/test_p03_semantics.py reports/review/P01/test_p01_processes.py reports/review/P01/test_p01_failure_counters.py reports/review/P01-r2/test_p01_r2_regressions.py reports/hardware/P01_FIX_R3_REPORT_TESTS.py reports/hardware/P01_FIX_R4_REPORT_TESTS.py --basetemp="$S0_PYTEST_TEMP"
```

## 真实包与安装路径

| 产物 | Bytes / 成员数 | Git 载荷 / metadata | SHA-256 |
|---|---|---|---|
| sdist | 192566 / 88 | 87 / 1 | `a8d136a6e9f7758a6eb5c6af2ce6c30ad400e1c986cc2918bf9bb6383f342b03` |
| 默认 wheel，由同次 sdist 生成 | 96674 / 47 | 42 / 5 | `d6e92c2e065c9190b8a1862ae091a59460a2131ef112d0b2225675d44e397634` |
| 显式 sdist 重建 wheel | 96674 / 47 | 42 / 5 | `d6e92c2e065c9190b8a1862ae091a59460a2131ef112d0b2225675d44e397634` |

实际成员集合、路径/链接、当前 Git/工作树字节逐项核对通过；两个 wheel 完全相同。本次未额外单独构建源码直接 wheel。未变共享归档边界脚本已在最终双 Python CI 运行通过，本地没有重复该调查。

新默认 CPU 隔离环境按锁文件和依赖 hash 离线安装 rebuilt wheel；清除 PYTHONPATH/PYTHONHOME，从源码外以 `python -I` 执行。全部 42 个源码/资源来自安装目录且字节与被审来源一致，未导入工作树生产包。

21 条命令含契约/五类 fixture、P01/data/tools CLI、registry、P02 原两份构建的 18 项制品比较、原创 P02 转换到 P03 raw parser 的实际衔接、10/10 scripted demo、原 P03-r2 的 31 项边界，以及原 P01-r3 的 13 项 launch 场景和真实报告 CLI。报告脚本未打进 wheel，明确从精确候选 Git blob 复制并单独绑定，所调用的库来自已安装包。42 份 stdout/stderr、13 组 launch 制品及摘要均核对 hash；31/13 是已有独立反例的安装复验，不新增独立样本。

未启动 child 的失败仍有 failed/ended_at/resources/summary，原异常对象保留，原生退出/RSS/未采样增长为 null；真实 child 的故障/预算/取消能回收，仅清理自有进程，正常退出 0/7 和无关进程对照保持。P02 manifest 仍为 `87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`；数据默认值未补入参数，未绑定历史工具仍拒绝执行。

## G1 分项结论及保留边界

| Gate | S0 结论 | 有效证据范围 |
|---|---|---|
| G1-SFT | PASS | 固定 MLX-LM 0.31.3；原始 BF16 Qwen3-0.6B 的 32 条原创 smoke、adapter 保存重载；Qwen3-1.7B 最终 1024/1536/2048 档每档 8 暖机 + 104 可测 SFT 微步。显式 completion mask、shift/EOS、参数更新范围和数学身份已独立检查 |
| G1-DPO 首选 | FAIL 保留 | mlx-tune 0.6.0 原生训练路径的 reference/ln(2) 失败，没有改写成通过 |
| G1-DPO 唯一备选 | PASS（限定配置） | mlx-lm-lora 3.1.2，显式 collator/mask、完整 frozen SFT-smoke reference、实际首累积周期 ln(2) 容差 2e-6、全程禁用编译、指定 checkpointing；每个通过运行只有 8 DPO 微步/1 次更新，保存重载和 adapter 更新范围已检查 |

原 [P01_REPORT](hardware/P01_REPORT.md) 与 [P01_RESULTS](hardware/P01_RESULTS.json) 保留其 T1 历史自测表述；本报告和原独立审查构成后续验收，不覆盖原文件。原 R1 已重核 17 组 CPU 数学和 185 项历史制品，r3 再核 92 份小型身份文件及不变源码。本次 S0 main 验证没有重跑模型、数学或大载荷 hash；沿用已经核验的精确绑定。smoke06-r2 的降级、smoke06-r3 的失败及 1536-r1 pressure 停止均保留。模型身份、模板和统计只适用于原校准格式，不能当作 ADR-0017 新格式的模型质量结果。

机器摘要 SHA-256：`b1b603dc68763cbf89969dde2356d92335a992504e3fcba4a8085d7337149326`；归档 inventory：`1a970a65e1ca8bdc7107a1240eccbcffe55a4d523a5607ed1789463a28962c00`；隔离摘要：`1cdcb20b5bb0815cbe75418d0c9f7472bfe03e8fbdeb043f021aaf7e829e6007`。摘要绑定全部 10 条实际命令、最终 CI/main、环境与驱动。06:22:51 UTC 共享 GPU 租约空闲，原人审副本仍 100 行、0 verdict / 0 reviewer，原 hash 保持。

G1 通过仅消除 P01 兼容性与工程前提。P02/G-DATA、共用格式独立验收及训练配置/窗口/响应上限绑定仍待完成；P04 的人工 token/mask 检查、真实模型 backend 和正式 SFT、P05 accepted-SFT reference 与长 DPO、P06/BFCL/隐藏评测、服务均未执行。本次没有新 GPU 作业、下载、费用、模型/数据上传或公网服务。
