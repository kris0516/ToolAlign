# S0｜P02 v3 主干技术验收

状态：**VERIFIED（CPU技术）**。2026-09-07 17:05:54 UTC 完成。[PR15](https://github.com/kris0516/ToolAlign/pull/15)普通合并为 `90c4da99f093b846a6b0ca0343d8293739ce2bea`；原候选 `5825d789ee89afedbfff31e828223608c6f435e2` 和独立 R1 PASS `dbd11d03e69c650efdb330f79ec380dd9914fa89` 均保留原 SHA。该验收提供整来源定点排除、三代选择 rank 绑定和既有材料复用能力。

## 精确集成与 CI

R1 的 P0/P1/P2 均为 0，原生 completed/idle；S0 接收核验 52,757 路径、1,235 链接、30 原命令及 11 源码时点，详见[接收与隔离集成](S0_P02_QUALITY_V3_INTEGRATION.md)。隔离普通合并 `424f1587002dfb4b0c46fa10ecbfbc3997c52c36` 实测 839 passed / 48 optional-tokenizer skipped，另有 21 个独立预期拒绝、6 个正对照通过。

最终 PR head 为 `04f299fae9d6f28220b19807fad082f5fc113a33`，base 为 `d71c827ab448832960b593a4e457cb5468096010`。[最终 CI 34145748913](https://github.com/kris0516/ToolAlign/actions/runs/34145748913) 的 Python 3.11/3.14 两 jobs 各 14 步全部成功，各自实际 839 passed / 48 skipped，另单独 46 项 P00 检查通过。重复运行不累计为新测试覆盖。

实际 CI 合并 `c63f99c6de2e1a63a71dca7031242372307c9ba0`、最终 head 和实际 main 的树均为 `0c1297e4a1a79b66ea75ac08e3347f52a4797bc3`；605 个文件逐字一致。最终 CI 证明为 `f6246e19fd831af2e51f47900e770bb88c13924dbe57f3ef4bd7542720ee6d17`。

## 实际 main 验证

七条实际命令全部 exit 0：两份新增 v3 测试文件共 **73 passed / 0 skipped**；R1 原独立边界程序的 21 拒绝/6 对照；显式 Git 跟踪 Python 文件的 ruff；冻结契约；605 文件公开扫描；`git diff --check`；三份现存归档与实际 main 的绑定。测试通过既有 CPU wrapper 运行，原始 argv、环境、UTC、子进程退出及源码首尾 hash 已保存。

新增测试为 `tests/data/test_quality_exclusion.py` 和 `tests/data/test_quality_exclusion_materials.py`；独立边界/归档入口分别为 [check_boundaries.py](review/P02-quality-exclusion-r1/check_boundaries.py) 和 [check_archives.py](review/P02-quality-exclusion-r1/check_archives.py)。归档核验使用 D1 已有 sdist/direct wheel/rebuilt wheel，分别 140/69/69 成员；139 个打包源码输入绑定到本次 main。

64 个既有安装包文件与 main 生产代码及先前实际安装版验证保持逐字一致。安装版 API 验证的执行时点仍是先前隔离集成；main 本轮新 build、install、安装版 API 执行均为 0，不改写原时间。

main 证明 `465cd283490649b118efed1d050ec69cf1ea17315e78c3bd8ada1760144359ef` 绑定 903 路径/11 链接；归档证明 `3aafacbb5c46045d69fe2d27de70f048f95d2624dbefdc77c833934cb1f25ae7`；既有安装绑定 `df62c80719cd6cb34ead56137e9d727186e199daf9dab9cffff12d890311252b`。

## 边界与接续

数据原文、旧 FAIL、辅助检查失败、原编码次数与测量时点保持。S0 本轮无新数据构建、编码、框架/模型/GPU、下载或业务 API；未增加费用、数据/模型上传或公网服务。Q1 正式审核在本 main 验证之后由 S0 接收，其实际质量处置和 G-DATA 决定见[独立质量接收](S0_P02_Q1_V3_ADJUDICATION.md)；原 main proof 中的 Q1 pending 保留原观察时间。真实 trainer 消费、模型容量和正式 P04 仍属后续范围。
