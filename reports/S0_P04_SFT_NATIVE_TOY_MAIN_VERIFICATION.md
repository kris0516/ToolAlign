# S0 原生 SFT toy 主干验证

2026-09-07；状态：**VERIFIED（固定原创数值部分）**。[PR11](https://github.com/kris0516/ToolAlign/pull/11)于2026-09-06 21:31:06 UTC实际普通合并，已读回closed/merged并同步本机main。此次验收覆盖默认CPU行为、新原生GPU toy数值/状态绑定和资源终态；正式模型训练、人工与G-DATA仍未完成，`training_authorized=false`。

| 对象 | 精确身份 |
|---|---|
| T1原候选 | `f7326d1823c4cf132ae44525f4755c96c88ec159` |
| 原独立R1 PASS | `67976fdcb33cba15caac8130213997bd330a7233`，P0/P1/P2均0 |
| S0隔离测试merge | `a1c467a98638ae2f92277e8177b549668335fe63` |
| 最终PR head | `397102c5702488ea6208675b9410b6352f0f82c6` |
| 实际main merge | `b2247d8f7d72d3376bdee92ae7840c5643a4ebdb` |
| 实际main/CI parents | `99392966b1170dcad2de63ab5e77a350a76da0e2` + 最终PR head |
| main/head/CI共同tree | `7fa29310d8b25c248c5a5a9c4b7f4fc309d3d5ab` |

[R1原审查](review/P04-sft-native-toy-r1/README.md)、[S0原件验收与实际集成](S0_P04_SFT_NATIVE_TOY_INTEGRATION.md)保留原SHA、命令时间、失败和警告。R1在独立原生任务使用gpt-6-astra/max完成审查并结束；S0按原SHA普通merge，候选源码/测试/配置及11份R1新增文件未变。main的426份Git文件与最终head及实际CI checkout逐字节相同。API仍返回的旧base字段482f899单独保留，没有用它冒充实际父提交。

最终[CI34061081859](https://github.com/kris0516/ToolAlign/actions/runs/34061081859)（CPU contracts第141次）双Python各14步骤全部成功：

| Python / job | 实际测试 | 原日志Bytes / SHA-256 |
|---|---|---|
| 3.11 / 101561612891 | 637 passed / 48 skipped；另46 P00 passed | 29042 / `6f3f0e2a9c78a3686bfacee74e44b9760b4db688c9be6a05f3fb3e8447a04072` |
| 3.14 / 101561613038 | 637 passed / 48 skipped；另46 P00 passed | 28924 / `ec51e3c89f508b5e5d07f4bfb073f0358f0fcf03492cd0c2a678dcadec1c3c67` |

两组48项skip均来自未提供固定私有CPU tokenizer及依赖：17数据alignment、18offline、13snapshot。Ruff、4契约、426路径公开扫描及241私有canary/18公开fixture的sdist/direct/rebuilt边界检查通过。完整原日志按返回UTF-8字节保存，实际checkout为`456696cb4f837d2f194693aca5b5f667c43eb327`，其parents/tree与上表一致；CI证明SHA为`54354c3bbf94ce8ede625a9da52b45828530b036d977b9569972ac6688bb040a`。CI默认组与本机完整组分别计量。

S0在实际main新执行六个不重叠CPU组：

| main组 | 实际结果 |
|---|---|
| cpu-combined | 931 passed, 2 skipped in 52.43s |
| original-format-review | 60 passed in 0.13s |
| independent-deadline-review | 2 passed in 11.56s |
| independent-training-binding-review | 13 passed, 110 subtests passed in 1.35s |
| independent-sft-cpu-review | 44 passed in 0.09s |
| independent-native-review | 34 passed in 0.81s |

合计**1084 passed / 2 skipped**。两项skip仅为HF reference专用snapshot cleanup。生产新增36项已在931中；110 subtests、此前R1/S0集成的1084及安装重复44项均不额外相加。全库/显式报告Ruff、4契约、426路径公开扫描和diff检查通过；本轮main命令无失败。每条保存实际argv、cwd、环境、UTC、退出码、原日志hash及426份开始/结束源码hash。

main直接重新解析S0集成时实际构建的三份现存归档，核对当前121份Git输入、58份包文件及metadata/entry point/license/完整RECORD。sdist为257973 bytes，SHA`b8c29ecad579ec43a06b31b9d6106d669dc74c0c50c13d785c861cff46062a17`；默认与显式sdist重建wheel各140688 bytes，SHA`0373c1adb1ae784391e82b06f6c93ab1519f593e68fec4c14c629829f83b5d3b`。main解析证明SHA为`b847229b3c6525bcfa0f4b565030c57b84bd234e90157bcfdaa95aa7652a7d02`。

**main本轮新build/install/API重跑均为0。** 原新target安装和7条隔离子命令实际发生在a1c467a、21:16:28–21:17:44 UTC；原native守卫发生在21:16:47 UTC。当前重新核对58份安装包文件、28个默认模块origin（含9个SFT模块）及25个native守卫origin，与main、归档和原执行源码相符。原7命令为origin、44项重复、help、完整prepare和三项预期拒绝（exit1/1/2）；另有native四项CLI与缺租约拒绝，无可选框架/源码回退。prepare SHA`6d7829d4f049e1a7a4727357a857a07d5834c654194286c913d78e32bca1dcb0`保持；更早CPU prepare的历史身份未改写。普通源码直接wheel仍NOT_RUN，CI canary direct另计。

以下13条main命令均实际成功，UTC日期为2026-09-06；前12条结果再由末条汇总：

| main命令 | UTC开始–结束 | exit | 原日志SHA-256 |
|---|---|---:|---|
| cpu-combined | 21:32:26–21:33:19 | 0 | `e832bfc619ab05fc07fa19c26a65011bea0736cf75127ba5ae5472fee720523e` |
| independent-deadline-review | 21:32:26–21:32:38 | 0 | `f30f9f0420f8920b956ccd24a301d6473e8cf43b4b57cf2fc01ca1b87e2e5af2` |
| original-format-review | 21:32:26–21:32:26 | 0 | `b40f7074b5c83beb3dfff0891b029118d9fc58ace31af2619271fdc35cab43e3` |
| independent-training-binding-review | 21:32:26–21:32:28 | 0 | `a96b7d6704fa7a08b7fafc5efb3066a2811a10458278a122f0c7f5c90b71516f` |
| independent-native-review | 21:32:26–21:32:27 | 0 | `4e40040d5a6cd60f32e96e8e07c0b15f9904960629f95c52f65e5c25aa423276` |
| independent-sft-cpu-review | 21:32:26–21:32:27 | 0 | `c520741a8f554448e43c37390b4fa4b2a9d5d6c83aca84f839c18420104aabd7` |
| lint-all | 21:33:08–21:33:08 | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| freeze | 21:33:08–21:33:08 | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| lint-explicit-reports | 21:33:08–21:33:08 | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| public-scan | 21:33:08–21:33:15 | 0 | `3733fdf146603b4a730045b2efb6022c6d467107ad9d68e3944edb9e3ec54785` |
| diff-check | 21:33:08–21:33:08 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| archive-verification | 21:33:08–21:33:10 | 0 | `79e2d90ea631269b7e33a4f47f0e2877c2fdee082b5e18aa35d7227a0f870c2d` |
| main-evidence-check | 21:35:57–21:35:58 | 0 | `5aa2e7b61b1407b2276f9c1e1877def33d4f1cdf6d3066f60d582c49dad23fe3` |

S0于21:35:57–21:35:58 UTC完成main汇总，核对591个实际文件路径；main证明SHA为`07d240a83632bec66026e643a4936469982c5ad80bec2855fa59d1f36f2a0d9a`。本轮34项CPU探针中的5个实际子进程（含历史反例）及4个截止时间子进程均已回收、当前PID不存在；启动失败场景无PID。当前监督器保存失败终态且可重登记fixture，旧控制器缺终态/重试阻断负例保持。RSS超限为明确故障注入，不是实际4GiB内存测量。共享GPU锁实际空闲。

原R1独立安装版框架2/2的数值/资源证据已验收：固定13 rank/64参数、8+5两个更新、完整44-token evaluate、实际checkpoint文件/参数绑定、选择和保存重载均通过2e-6对照；单段丢5尾微步为EXPECTED_NEGATIVE。S0本轮没有新增框架运行，原T1三次与R1两次的时间、源码epoch和结果不改写为main执行。原CPU上游KeyError、padding反例、shutdown warning及所有辅助初稿失败仍在；对三个确切semaphore名的只读ENOENT检查不代表全局泄漏审计。

100行语义表与13行token/mask表仍0 reviewer/0 verdict/0 notes，实际页面观察0；没有代填或绕过原导航拒绝。新真实13例/8228行编码、选择物化、预训练模型/真实P02优化均为0。该子包VERIFIED后，P02整包/G-DATA、实际页面与两项人工、真实0.6B容量、正式1.7B baseline/SFT/DPO、评测、服务和P09完整交接仍待完成。完整P00–P09目标保持，费用、公网推理及模型/数据上传无新增授权。
