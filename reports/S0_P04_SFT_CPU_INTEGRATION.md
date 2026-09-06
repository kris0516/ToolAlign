# S0 SFT CPU准备独立验收与隔离集成

2026-09-07（本轮执行UTC日期为2026-09-06）；状态：**ACCEPTED（CPU准备部分），最终CI/main待验证**。[PR10](https://github.com/kris0516/ToolAlign/pull/10)保持Draft。完整原生trainer仍BLOCKED_UPSTREAM_CPU_ENTRY，配置`training_authorized=false`；实际页面、kris语义/token-mask审查、G-DATA与正式P04仍未关闭。

| 对象 | 精确身份 |
|---|---|
| T1完整候选 | `33d6248e2c518ea777618224382bd30a3cc3433d` |
| 独立R1 PASS / 唯一父 | `800480b0b1e14c21937f1b5073daf543a2ba31fc` / 上述候选 |
| R1 tree | `d4cb8138dd62d4ed614c6f1a8cb5f43c39f00f1a` |
| 集成时main | `ad8115a33c8cccd3849d0286424d0c1b77e5d6c2` |
| S0普通merge / parents | `487c92dfd552a2992e707301dc4a7d6edeb94f36` / 上述main与R1原提交 |
| S0实测tree | `32755669cc609850ec9bf54ea8863523fd256eba` |

R1按完整d65592e、gpt-6-astra/max在独立任务完成审查，CPU准备PASS/P0/P1/P2均0，并已原生completed/idle。审查只新增9份文件、候选384文件和364份原基线未变；[报告](review/P04-sft-cpu-r1/README.md)、[机器索引](review/P04-sft-cpu-r1/VALIDATION.json)、[交接](../coordination/handoffs/P04-sft-cpu-review-r1.md)保持原SHA。

S0于17:33:51–17:33:55 UTC逐字节核对56,134个实际文件路径、26条R1原命令及21条公开索引映射、7条安装子命令和实际Git对象。含旧50,685私有文件、1,562上轮封存条目、283旧链接及本轮1,673封存文件，集合有重叠，不相加为测试分母；另核对completion和末次生成回执。R1最终保留178,736,069 bytes，低于2GiB，所有66个旧ref对象及旧审查分支保持。原未去敏审查只在本机且不是公开祖先。completion SHA为`eedcb6c870b8847cfc9f389d7d41c535bfcfb3299dcd02855193882855e22c31`；S0证明SHA为`07b6935e087d0d7626922f6db93d8536a35539bdfc5f9ec67bd90a8f97a63ef6`。

CPU可接收范围为固定输入的`python -m toolalign.training.sft` prepare、只读train/validation视图、共用Sequence/pad_sequence的collator、累积计划和validation/Score结构。完整原verifier、smoke1600/197与formal6013/217、13例完整原IDs/数组和8项固定输入/输出拒绝经R1核验；没有新增真实13例编码、8228重编码或selection物化。原目标全为tool_calls，三类协议例单列。

R1仅一次持租约CPU子进程对13条原创小例核验loss/gradient：最大误差分别为2.384185791015625e-07和8.940696716308594e-08，均小于2e-6；padding及ignored-logits不变量通过。S0另用保存的float32数值和标准库独立重算CE/完整梯度，证明`6c9c71a6c26a499c31014a0ed7a6c6c0bdfe0dfbb2cdd67db2daf11e2e773a1a`。未修改的MLX-LM train在CPU设备元数据读取处KeyError，实际iterator访问0、optimizer更新0、checkpoint0、参数hash不变。R1捕获预期反例后child exit0，不是训练成功；实际进程回收和租约释放已核对。S0没有新增框架数值replay。

`train_toy_segments`、`post_update_score`不能作为已验证原生trainer使用。实际8+5微步、尾周期数值、native evaluate、checkpoint保存重载/post-tail绑定仍NOT_RUN；200/752是计划，结构测试不证明原生更新。旧T1两次exit1及R1的ruff初稿/临时ref保全假设两项辅助失败完整保留。S0此前intake的路径假设、数值hash的dtype命名假设失败，以及本次将整数模块计数当列表的检查器TypeError均保留原脚本/日志/回执，修订后核对通过；均未修改候选或原始证据。

S0在新隔离worktree普通merge后实际执行五个不重叠CPU组：

| 组 | 实际结果 | pytest耗时 |
|---|---|---:|
| tests与既有P00/P01/P02/P03独立回归 | 895 passed / 2 skipped | 53.50s |
| 原格式结构与统计边界 | 60 passed | 0.11s |
| 原截止时间边界 | 2 passed | 11.59s |
| 原训练绑定边界 | 13 passed / 110 subtests | 1.21s |
| 本轮R1原创SFT CPU边界 | 44 passed | 0.08s |

合计**1014 passed / 2 skipped**；两项skip为HF reference专用snapshot cleanup。T1新增51已在895内，110 subtests与安装重复44项不再计入。Ruff全库/显式新报告、4份冻结契约、399路径公开扫描和diff检查均通过。每条回执的399份开始/结束源码与实际Git一致；全部src/tests/configs保持候选字节，集成仅组合main与原R1，不更改被审实现。

S0使用已有CPU解释器及只读缓存依赖实际离线构建三份新归档，逐成员检查118份sdist Git输入、57份包文件、metadata/entry point/license及完整RECORD：

| 本轮S0实际制品 | Bytes | 成员 | SHA-256 |
|---|---:|---:|---|
| sdist | 243688 | 119（118 Git+PKG-INFO） | `54ca695f640014ac03128e5dd33534d913f097c8a22019af7fae90f746183655` |
| 默认wheel | 129868 | 62（57包文件+5metadata） | `936256e277cdf3ae7c43668dc4ad358c4249de24a17273e721936f7584cbee33` |
| 显式sdist重建wheel | 129868 | 62 | `936256e277cdf3ae7c43668dc4ad358c4249de24a17273e721936f7584cbee33` |

新归档全字节与T1原件/R1解析结果一致，S0有独立构建日志与UTC。默认wheel实际由sdist生成，普通源码直接wheel仍NOT_RUN，CI canary direct路线另计。归档证明SHA为`cbb340c64f0ab50eea39ccd7d536700e457d4d452acb89cafecb12d79bcc4400`。

新默认wheel已离线无依赖安装至S0新target。在非源码cwd使用-B/-I/-S和原R1检查器运行7条子命令：origin、44项原创重复、help、完整prepare、原输出存在/配置篡改/训练开关三项预期拒绝（exit1/1/2）。27个ToolAlign模块含8个新模块均来自新target，57包文件与Git/归档一致，11种可选库不可导入。安装版prepare与R1原结果逐字节一致，SHA为`52cd77a04e12417b18dafae7a6447dfe1007a57780434743a4ace076d87da4c9`。没有新环境/依赖下载、原真实13例或8228重编码、原数据/selection新增物化；回归中的固定CPU tokenizer例按本轮命令执行。

下表是16条实际成功命令，UTC日期均为2026-09-06。完整argv/cwd/环境/源文件hash保存在本机原始回执，未重构命令冒充执行。

| 命令记录 | UTC开始–结束 | exit | 原日志SHA-256 |
|---|---|---:|---|
| cpu-combined | 17:36:38–17:37:31 | 0 | `96f32878116aa9b11a5b7dff65e5aa2a90fd94c80ffa4551cd1796f14697f523` |
| original-format-review | 17:37:31–17:37:32 | 0 | `b746f5b04deb9a4a5ab9ad150ef96de12b7adc51f3b8f0c709ce03184f5e8501` |
| independent-deadline-review | 17:37:32–17:37:43 | 0 | `1ac285189481bb85a7f4c86eb49cfefa8c858cbb47ed0435c18bafb4cbdc6641` |
| independent-training-binding-review | 17:37:44–17:37:45 | 0 | `dc4bab8d230d3ebd008b50d3bf2af7a80811954fc11e10e5ff63a8e1572a0d6f` |
| independent-sft-cpu-review | 17:37:45–17:37:45 | 0 | `18b4045681189cd2509eb491e43dbeaa10e75d710a029e2c69e724be81a14604` |
| lint-all | 17:37:45–17:37:45 | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| lint-explicit-reports | 17:37:45–17:37:45 | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| freeze | 17:37:45–17:37:45 | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| public-scan | 17:37:46–17:37:51 | 0 | `bd203b7dfe0aff786d49e90c75ff4e19c20fe99ffca22334012aaf2e9d4cabbe` |
| diff-check | 17:37:51–17:37:51 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| build-default | 17:38:12–17:38:12 | 0 | `966788833cc9907e7e090c4f97396c2e26dabc14e972aacdf951482d51365ce4` |
| build-rebuilt | 17:38:12–17:38:12 | 0 | `13703a4f53fc419ddb23729bb9e29d529dae36b8aee372af03acaebd778de61c` |
| archive-verification | 17:38:12–17:38:14 | 0 | `dc92477fe555b5dbfa612feb98edcb15753809fe15c76ae2be2bda25ef2abb57` |
| install-default-wheel | 17:38:14–17:38:14 | 0 | `ec4c912c4d21acb71a7736c74fc810c0960de4a5f31c2bd3f2ab6c56167bfff1` |
| installed-sft-api | 17:38:14–17:39:07 | 0 | `7a05634a95348b8d856870ded96af8042ef916b04708acf049afdd3bd2b0d58d` |
| integration-evidence-check | 17:40:42–17:40:43 | 0 | `49d501ca11eaa62b884794fa8862cc100289aa4c749cadd019888f3539d41479` |

17:40:43 UTC汇总核验通过，证明SHA为`15680ada768366d850cba4f6b7cfc9cbf8ee44068f8f8a3bf2bac44a2f06d09b`。四条本轮截止时间子进程记录确认wait/reap、handle关闭、目录清理，PID均不存在；共享GPU锁实际空闲。本轮文件占用观察值144,951,220 bytes低于2GiB，是收尾时点计数，不是不可变seal或RSS测量。100行语义与13行token/mask表仍0 reviewer/0 verdict，实际页面观察0，原浏览器拒绝与未完成项保留。

最终CI、PR合并与实际main验证继续由S0完成；本次CPU准备接收不关闭完整P04、人工、真实模型容量、baseline/SFT/DPO/评测或服务部署。没有预训练模型加载、费用、公网接口或模型/数据上传。
