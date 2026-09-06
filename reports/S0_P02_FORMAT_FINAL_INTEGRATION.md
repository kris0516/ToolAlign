# P02 格式与截止时间修订｜最终组合验证

2026-09-06，S0。**新最终组合的本地 CPU 与实际归档检查通过；本记录写入时，最终 GitHub CI、合并及 main 验证尚未完成。** 格式修复和截止时间测试修订均已获独立 R1 PASS；原失败及旧测量仍保持原身份。

## 精确输入与普通集成

- 格式候选 `8c439f683b9d6b04919ff1f7184d8924ccf82f9f`，原独立审查 `b9f7567d7c1066eeb0bff7c47033bb2771eb9594`，PASS、P0/P1/P2均0。
- 截止时间候选 `947144fa2dd248113f6db412f120cdae5483c9b8`，原独立审查 `1531892a9e49b69283ef07f3142b221693483628`，PASS、P0/P1/P2均0。[交接及S0核验](S0_P02_FORMAT_CI_FOLLOWUP.md)保留657项CPU与另2项独立边界探针的原始范围。
- 从原最终候选 `2b11b7fad69957324ecfa671bac71552ec3501b7` 普通 merge 原1531892，产生 `cd66dcfdf872fdf97d3bd7679c04026a7205b92c`；再普通 merge main `6a53a07c55caa3a9683a588bdd43eb76a71792c3`，得到实测组合 **`6108c08015f70ef1583480856c920eb7e51429fc`**，tree `d72b02d0acad09a56a89d5a0f3bb05a68e629062`。

336份组合文件逐字节核对：8份main协调变化与11份E1/R1变化不重叠，其余来源保持。原格式FAIL审查2942e568、修复8c、两份PASS审查均保留原SHA与祖先关系；原未去敏审查不在公开祖先。47份生产包源码/资源与README、LICENSE、pyproject和uv.lock共51份包输入等于原2b。证明SHA-256 `d98df27d904e18dfeea7f0e8d65cdb94fda1cbdf5017e771d483d79beac93b1d`。

## 实际 CPU 验证

11:09–11:10 UTC，复用既有纯CPU环境及固定本地tokenizer，全部命令记录实际argv、环境、Git/tree、UTC、退出码及日志hash。三个pytest调用互不重叠：

| 实际范围 | 结果 | 原始日志SHA-256 |
|---|---|---|
| tests及既有P00/P02/P03/P01独立回归、P01-r3/r4报告检查 | 781 passed / 2 skipped，52.14s | `a145e4115ec57c8f7dbf700c790bdcae5e53c27b8a4f588db00dc8b88c57a7b8` |
| 原R1格式结构和统计两个文件 | 60 passed / 0 skipped，0.10s | `6279136f10e7afff61d1aaf2285e31851be7611224c92cc18592304e0e8aa9c3` |
| 新R1截止时间独立边界文件 | 2 passed / 0 skipped，11.59s | `1ac285189481bb85a7f4c86eb49cfefa8c858cbb47ed0435c18bafb4cbdc6641` |

合计 **843 passed / 2 skipped**；两项跳过仍为native环境的HF专属清理测试。目标三例已包含在781中，不再另加。新边界探针执行真实进程/目录清理与约10秒watchdog控制；测试时钟的700/1100ms仍不作为性能数据。Ruff、4份冻结契约和336路径公开扫描通过。

第一组与[原组合预检](S0_P02_FORMAT_PREFLIGHT_R2.md)使用相同完整路径集合，但当前tests已包含E1新修订；原R1格式组为`reports/review/P02-format/test_independent.py`及`test_audit_denominators.py`，新独立组为`reports/review/P03-ci-deadline-r1/test_deadline_boundaries.py`。三组使用各自新的pytest临时目录，未改全局收集规则。

## 三份实际新归档

11:10 UTC实际运行离线`uv build`生成sdist和默认wheel，再从该sdist显式重建wheel。11:16 UTC直接解析完整成员、核对Git字节、metadata及wheel RECORD：

| 归档 | Bytes / 成员数 | SHA-256 |
|---|---|---|
| sdist | 214091 / 101 | `7f0cbda908e3452e1e47fde169daeea98f16fbc9eebc1fef126cc6ba8e3974bb` |
| 默认wheel，由同次sdist生成 | 107033 / 52 | `6c5674e403f27008b64e119b07def38e122856f958be4942358e23be336f1721` |
| 显式sdist重建wheel | 107033 / 52 | `6c5674e403f27008b64e119b07def38e122856f958be4942358e23be336f1721` |

sdist为100份Git文件加PKG-INFO；两个wheel各为47份生产源码/资源加5份metadata，完整字节彼此相同，也与原组合预检实际安装的默认wheel相同。归档证明 `5a75c2d65ca2d9606cfcc45e1641f7f22ab18c55e375a02344e868dbf8cd7800`，通过日志 `ac7c80dc52784027c99f9d46ba966d48a20e27aea2ec79817ee9195b2ab46119`。

原组合的10条默认安装/接口命令及安装版两engine原F1回归保持其实际08:42–08:55时间和输入；本轮新安装命令0，不把相同wheel的旧安装测量改写为新运行。源码直接wheel、模型/GPU和完整8,228行新重跑均NOT_RUN。

S0首次归档核对脚本漏列构建工具自动附带的`.gitignore`，exit1日志 `ef1d9ed5316793e7f21bad6295f5c939b07e2123730b1364c6af85deb3ac5863` 与原脚本保留；补入该确切Git文件并使用已观察的旧wheel路径后通过。归档及被审实现未改。包含此失败的11条实际命令摘要SHA-256为 `8032dc0943bb31e002d638f757d0bd52e681ad5a1842f345343d12e39aaa8c89`。

## 尚未完成的门槛

下一步把本报告作为文档提交加入实测组合，确认可执行与打包输入未变，普通推送PR8后检查精确新head的Python3.11/3.14全部CI步骤，再合并并验证实际main。旧[CI34024093376失败](https://github.com/kris0516/ToolAlign/actions/runs/34024093376)保持；本地通过不替代最终CI。

原数据、8,228行表示测量、全部split/目标/manifest、人审材料与历史失败保持。11:01 UTC共享GPU租约空闲，人审副本100行仍0 reviewer/0 verdict；G-DATA、训练绑定、P04人工token/mask及正式训练/评测尚未完成。新格式技术验收不等于这些阶段通过。
