# S0 原生 SFT toy 独立验收与隔离集成

2026-09-07；状态：**ACCEPTED（固定原创数值部分），最终 CI/main 待验证**。[PR11](https://github.com/kris0516/ToolAlign/pull/11)保持 Draft。R1 对精确候选正式 PASS，P0/P1/P2 均为0；S0 完成原件验收、普通合并和以下实际集成检查。正式 P04、G-DATA、人工与真实模型容量门槛仍未完成。

| 对象 | 精确身份 |
|---|---|
| T1 完整候选 | `f7326d1823c4cf132ae44525f4755c96c88ec159` |
| 原独立 R1 PASS / 唯一父 | `67976fdcb33cba15caac8130213997bd330a7233` / 上述候选 |
| R1 tree | `37b7601d6f04ce065bdeb9d44d6ed2175366942e` |
| 集成时 main | `99392966b1170dcad2de63ab5e77a350a76da0e2` |
| S0 普通 merge / parents | `a1c467a98638ae2f92277e8177b549668335fe63` / 上述 main + 原 R1 |
| 本轮实际测试 tree | `c1b90892e4acbe3c42044034d5d73725e88dc304` |

[R1 报告](review/P04-sft-native-toy-r1/README.md)、[机器索引](review/P04-sft-native-toy-r1/VALIDATION.json)及[交接](../coordination/handoffs/P04-sft-native-toy-review-r1.md)保持原 SHA。审查仅新增11份文件，408份候选保持；集成的424份Git文件逐字节等于当前main加候选9条授权改动、再加原R1的11份新文件。没有隐藏修复、重写审查历史或改变原测试收集。

R1原生本轮于2026-09-06 21:02:29 UTC completed/idle，远端审查分支与原提交一致。S0于21:09:56–21:10:04 UTC完成最终核验：58,108个实际文件路径、809个链接原目标、38条原R1命令（含29条测量索引）、原T1及R1的源码/数值/安装/保全链。计数含重叠集合，不能相加为测试分母。R1最终封存2281文件、173链接、8个根目录；加manifest/completion后169,710,259 bytes，低于2GiB。completion SHA为`d9f1b836235d42c51a020e9456799b19f10fb874102b0034ff6e2381452cc672`，FINAL_FILES SHA为`e9ec90b083b146421bac9839eb1147f2ba37a02dd3468425273a895782fd1a8a`；S0最终验收证明为`ff2bccbfddfa71875775e53620d622b9838fa7b121433f3cf94df33df05a408f`。

R1独立新安装target实际完成原13个rank、64参数的8+5两次SGD更新、每状态完整44-token evaluate、checkpoint选择及保存重载。标准库参考独立推导全部梯度并复核832个中心差分分量；原13 rank的12种数值载荷没有去重。实际step1/step2 CE分别为2.066978758031672、2.0616965131326155；checkpoint SHA分别为`06f9f5dcc8dbc6e399313eaac83b4506d90521f24793644b29c0c15fe43df58b`与`17906c78b9689f4e75768eb2bbe23ce5853db2a66833e295b10b2fa9436eb132`。CE、完整梯度、参数和重载均满足固定2e-6容差；错误checkpoint绑定被拒绝。该验证集复用toy训练例，只证明数值与状态记账。

R1新框架额度2/2已用完。第二次直接观测单段accumulation=8只更新一次、丢5尾微步，是EXPECTED_NEGATIVE。两次实际墙钟为4.496296458877623/3.140921541955322秒，采样RSS为400310272/400392192 bytes，MLX peak均5864 bytes。真实R1共享OS租约在框架导入前持有至进程退出；实际2412/2411模块来源、30个ToolAlign安装来源、GPU default/stream、Torch CPU/2+2线程及回收均已核对。此处复述原运行，不是S0新框架replay；完整原件核验见[S0交接跟进](S0_P04_SFT_NATIVE_TOY_HANDOFF.md)。

S0在上述实际merge上新执行六组CPU检查：

| 本轮组 | 实际结果 |
|---|---|
| cpu-combined | 931 passed / 2 skipped |
| original-format-review | 60 passed |
| independent-deadline-review | 2 passed |
| independent-training-binding-review | 13 passed / 110 subtests passed |
| independent-sft-cpu-review | 44 passed |
| independent-native-review | 34 passed |

合计**1084 passed / 2 skipped**，两项skip仅为HF reference专用snapshot cleanup。生产新增36项已含在931内；110 subtests、R1先前1084及安装版重复44项另记。全库和显式报告Ruff、4份契约冻结、424路径公开扫描、diff检查通过。本轮18条S0集成命令全部exit0；每条保存真实argv、cwd、环境、UTC、日志hash与424份开始/结束源码hash。

S0新构建并解析三份实际归档，核对121份sdist Git输入、58份包载荷、metadata、entry point、license和完整RECORD；归档字节与已审原件一致。sdist为257973 bytes，SHA`b8c29ecad579ec43a06b31b9d6106d669dc74c0c50c13d785c861cff46062a17`；默认及显式sdist重建wheel各140688 bytes，SHA`0373c1adb1ae784391e82b06f6c93ab1519f593e68fec4c14c629829f83b5d3b`。两次raw构建日志均明确从sdist构建wheel；普通源码直接wheel仍NOT_RUN。归档证明SHA为`5ca2daab070193e83db68dd4b5bb5b0bba54eac288e6f31d265178c4ca4eae81`。

S0用现有默认环境离线、无依赖下载安装到新target。7条`-B -I -S`非源码cwd子命令验证来源、原44项重复、help、完整prepare与三项预期拒绝（exit1/1/2）。58份包文件和28个实际默认模块origin（含9个SFT模块）逐字节相符，无可选框架或源码回退。prepare SHA`6d7829d4f049e1a7a4727357a857a07d5834c654194286c913d78e32bca1dcb0`与原R1/T1本轮安装输出相同；旧CPU prepare的历史身份不改写。另一个隔离进程验证native的help、FORMAL模式、输出范围与配置hash拒绝，以及无租约时在框架导入前拒绝；25个已加载ToolAlign模块均来自新target。

本轮新CPU探针保留5个实际自有进程（当前4个加历史反例1个）及启动失败的无PID场景。实际9000字节文件/8192字节测试阈值、identity/monitor/stdout故障与明确注入的RSS报告均分别记载，注入RSS不是内存测量。当前失败均有终态并可登记第二次fixture reservation；旧控制器缺终态/重试被拒绝的反例保持。5个PID当前不存在、fixture租约空闲，另4个截止时间子进程已reap/关闭handle/清理目录且PID不存在。

以下18条命令均实际执行，UTC日期为2026-09-06；原日志不改写为稍后的最终head或main执行：

| 命令 | UTC开始–结束 | exit | 原日志SHA-256 |
|---|---|---:|---|
| independent-deadline-review | 21:12:55–21:13:07 | 0 | `d2cb4efd13f239e23ff58de3cbb490b6cca671b73df5cf4dc0b05ad455903274` |
| cpu-combined | 21:12:55–21:13:53 | 0 | `9244c8affb94d51c6f3a69967a86c34709d6d4663b0f7077b9cba23795a64ac8` |
| original-format-review | 21:12:55–21:12:56 | 0 | `0f3abf87862ef23c15a27a12d235752b1deed665556c47771801a7583723db22` |
| independent-training-binding-review | 21:12:55–21:12:57 | 0 | `39ddf6be4a373806b591898b3988b17414eca0808e6dd5b9234135aca0ef4723` |
| independent-sft-cpu-review | 21:12:55–21:12:56 | 0 | `aeb8cb6770286886c05ea14d31855f64694b474b6dd7ccf34795ac318140e2e6` |
| independent-native-review | 21:12:55–21:12:56 | 0 | `7b39c9b2a80d4255d19e8a52e880560278af39219d368269c21dcbd9e9768e94` |
| lint-all | 21:16:17–21:16:17 | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| public-scan | 21:16:17–21:16:24 | 0 | `e08f17e44a1c23cb9f2f9d6c346421c159e879a1e681bb6b3fbfc9a0e6ac9664` |
| freeze | 21:16:17–21:16:17 | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| lint-explicit-reports | 21:16:17–21:16:17 | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| diff-check | 21:16:17–21:16:17 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| build-default | 21:16:27–21:16:28 | 0 | `966788833cc9907e7e090c4f97396c2e26dabc14e972aacdf951482d51365ce4` |
| build-rebuilt | 21:16:28–21:16:28 | 0 | `13703a4f53fc419ddb23729bb9e29d529dae36b8aee372af03acaebd778de61c` |
| install-default-wheel | 21:16:28–21:16:28 | 0 | `16374ad88122a77253029376e53f18bc0b524629f303b391af53006e9836464d` |
| archive-verification | 21:16:28–21:16:30 | 0 | `83eef8415577775c4cb18a71f7aab0f7b7e8be46936767ed346bb0037a0e669b` |
| installed-sft-api | 21:16:47–21:17:44 | 0 | `7a05634a95348b8d856870ded96af8042ef916b04708acf049afdd3bd2b0d58d` |
| installed-native-guards | 21:16:47–21:16:47 | 0 | `eeb7676277cdae2a5cb9a848872dff6a5d76e1ed1532545626c0f719881fc2f7` |
| integration-evidence-check | 21:21:01–21:21:02 | 0 | `16a7c67f27d0b11b660ca1c50e7e76af67d642246e8a2adadc7f6158c68b0377` |

S0于21:21:01–21:21:02 UTC完成汇总，重新核对600个实际文件路径；证明SHA为`af492409909d11df1e6d5e36819ba83f49145050280e126fbff8596134eac4f1`。当时新增私有材料145,903,927 bytes（汇总输出仍在形成，属于时点清单），共享GPU实际空闲。100行语义表和13行token/mask表仍0 reviewer/0 verdict/0 notes；未写人工字段或重新尝试已拒绝的页面导航。

原CPU上游KeyError、单段丢尾、原default_loss padding反例及三次shutdown warning全部保留；三个确切semaphore名的只读ENOENT检查不解释为全局泄漏审计。R1的三份辅助初稿失败及S0数值consumer集合、旧链接schema的审计初稿失败均保留，只修正审计器；本次18条集成命令没有失败。

S0新增框架运行、预训练权重、实际13例/8228行新编码、选择物化和真实P02优化均为0。`training_authorized=false`。最终PR CI及main验证待完成；P02整包/G-DATA、实际页面、人审、真实0.6B容量、正式1.7B baseline/SFT/DPO、评测、服务和P09完整交接仍未完成。费用、公网推理和模型/数据上传没有新增授权。
