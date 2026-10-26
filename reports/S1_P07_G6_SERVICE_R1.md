# G6｜真实受限 CUDA 服务、Mac 客户端与交付

2026-10-27，S1。**Mac→SSH loopback→Colab L4 的固定 M1 服务已实际运行：11次生成尝试中10次返回、1次主动取消；两次缓存命中、跨principal隔离和取消后的新worker重载有完整证据。** 两个CUDA child和两个Mac工具child均回收，71份远端文件已验证回收，唯一实例已停止。累计分配837.615秒，账户余额观测差0.25 CU。[R1技术终验](reviews/P07_G6_FINAL_R1.md)与[Q1实际AI材料终验](reviews/P07_G6_FINAL_Q1_R1.md)均PASS，S1已回读接纳；最终交付见[PR36](https://github.com/kris0516/ToolAlign/pull/36)。

实际CLI把1536 KiB正确换算为1.5 MiB两次，但第三次模型动作仍要求调用工具，因两轮上限结束，没有最终回答。无需工具请求返回了未声明的`tool_0`。这些观察支持交付受限接口和保留失败记录，后续能力改进应单独验证最终回答、停止和无需工具判断。本轮没有新增训练或替换失败样本。

## 源码、输入与运行身份

- 实际源码为[PR35 main `aaab0171246feaf307ad2c626108e94383e438d9`](https://github.com/kris0516/ToolAlign/commit/aaab0171246feaf307ad2c626108e94383e438d9)。最终候选`8cc8ad941a8c7cd328b49835da5bbcaba375adc4`的双Python CI 40412567146全部成功；main与受检头完整文件树相同。132份运行时包文件及48个依赖版本已回读核对。
- M1为Qwen3-1.7B revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`加G3 step743；完整训练状态SHA256 `cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14`，adapter SHA256 `973c440e29090892ad11d6d56b94bad4c98a5398c223e2b4302d7dba7c4640ed`。BF16、未量化、原模板、temperature .7/top_p .9/top_k 0、thinking=false、256输出/2048上下文均保持。
- 在首个输出前冻结四个原创开发输入、顺序、seed42、模型、配置与11次上限；冻结索引SHA256 `0d1cdb5efa67150adb34ae5606a722171ad997e0b9dcd8258f7087a9f57ad4d7`。配置SHA256 `8128aac4c67b2f6d7f46b39a562e2257b3568cc6a8fe09f5f78bf5586832787b`；原计划、认证和完整原文留私有。没有使用G5隐藏题构造本轮输入。
- 服务实际只监听`127.0.0.1:18761`，Mac以OpenSSH本地转发连接；实际HTTP的run、源码、checkpoint、依赖与模型身份一致。认证文件权限0600；执行记录与71份回收文件均未包含真实token值。

## 实际请求与工具结果

| 次序 | 请求用途 | API终态 | epoch | cache hit / prefill tokens | 服务完整wall（秒） |
|---|---|---|---:|---:|---:|
| 1 | A首次单位转换 | completed | 1 | 0 / 581 | 4.282005 |
| 2 | A相同输入 | completed | 1 | 580 / 1 | 3.618861 |
| 3 | B相同输入 | completed | 1 | 0 / 581 | 3.678111 |
| 4 | B相同输入 | completed | 1 | 580 / 1 | 3.648646 |
| 5 | 切回A | completed | 1 | 0 / 581 | 3.647804 |
| 6 | 观察running后取消 | cancelled | 1 | 未完成计量 | 0.565047 |
| 7 | 重载后A相同输入 | completed | 2 | 0 / 581 | 4.310193 |
| 8 | 无需工具 | completed | 2 | 0 / 406 | 2.555139 |
| 9–11 | 真实CLI三次决策 | completed各1 | 2 | 0 / 584、746、908 | 4.043785、4.092276、4.039578 |

`completed`表示模型响应完成。10份完整响应均能解析为Action JSON，全部为`tool_calls`。第6次已计入11次尝试，生成token数与内核执行进度未完成记录，不补为零。

第1–5、7次返回正确的3.5 min→s调用，未在这组单决策请求中执行工具或取得最终答案。第8次advertised工具为空，原文却请求`tool_0`；该单决策观察没有交给本地工具执行器。

第9–11次使用真实`python -m toolalign.client run`。Mac独立解析原文并经固定registry执行前两次合法换算，实际观察均为1.5 MiB；两个工具child均回收。第三次动作仍请求换算，在执行前命中`tool_round_limit`，CLI退出1，状态`budget_exhausted`，`final_action=null`。轨迹决策/完整wall均为14.378113秒，额外清理尾段0；生产入口保留`semantic_outcome=not_scored`，不制造模型成功率。五类原创CPU scripted案例另见[示例说明](../examples/service/README.md)与[独立CPU复现](reviews/P07_G6_INTEGRATION_CPU_R1.md)。

## 缓存、控制边界与回收

两对相同principal/input的原始输出逐字节相同，并有580个真实命中token、1个实际prefill token；切换principal及重载后均miss。首次请求prefill 433.168ms，随后命中76.485ms；该差包含首次CUDA执行效应。已warm的B序列prefill为81.391→77.706ms，服务wall为3.678111→3.648646秒。该序列证明复用与隔离，不估计稳态吞吐或P95。

真实HTTP另验证：同key/同body回读原请求，不增加生成；同key改seed返回409；B查询/取消A的请求均404；不存在key的只读查询404；修改advertised schema返回400；错误token返回401。服务最终仅11条accepted、11次尝试，与冻结清单、Mac回执、远端input/terminal及10份完整backend指标一致。

取消在Mac实际读到`running`后发出；epoch1的真实进程回收、目录清理与GPU lease释放均有记录，清理耗时0.194649秒。`running`是调度状态，不能单独证明取消时CUDA内核已开始。新PID/epoch2完成prepare后才重新ready，固定模型身份不变，第7次cache为冷状态。

第11次完成后，生成次数上限使epoch2 child回收，清理0.207328秒；随后定向SIGTERM结束仍保留只读控制面的HTTP父进程，退出0。该SIGTERM没有再次清理活跃CUDA child；CPU独立审查已覆盖父进程信号下的实际owned child。CUDA硬截止分支、本次部署回滚均未运行。实例停止前两个CUDA child的`reaped/directory_cleaned=true`、原owner不再持lease；两个本地工具、CLI父进程及两次SSH转发进程也均已回收。

## 计时、资源与失败记录

| 口径 | 实测 |
|---|---:|
| 固定模型文件完整预检 | 12.036396秒 |
| 首worker cold load / prepare | 6.765106 / 6.956720秒 |
| 重载worker cold load / prepare | 6.592775 / 6.783241秒 |
| 服务wall（含预检至收尾） | 106.491290秒 |
| Mac完整smoke（含ready、控制探针和CLI） | 61.742070秒 |
| CUDA峰值allocated / reserved | 3469.662 / 3592 MiB |
| 设备显存采样峰值 / 实际总显存 | 3856 / 23034 MiB |
| 远端产物 | 71文件、137629 bytes |
| 唯一L4完整分配 | 837.615324秒 |
| 账户余额前→后 / 观测差 | 166.20→165.95 / 0.25 CU |

cold load从tokenizer到CUDA ready，不包含父进程完整文件预检；prepare包含worker握手。请求wall从accepted到terminal，包含排队与必要清理；child generation另保留原计量。104次设备样本约每秒一次，采样峰值不等于PyTorch allocator峰值；取消中的部分生成计量缺失。累计分配包含安装、空闲、失败连接、模型/检查点传输、运行和回收，低于首次3600秒及累计7200秒/4CU上限。停止后fresh sessions为0、active assignments为0、usage rate为0。

原环境/控制失败保留：系统缺`ensurepip`后按已批准版本安装`python3.12-venv`；安装SSH连接中断，但原安装进程随后退出0，没有重复安装；在转发隧道占用连接时启动SSH被Colab以HTTP429拒绝，关闭隧道并确认未启动后才启动后台服务，再建立转发。没有因此重复模型请求。S1只读审计脚本首次有两处缺右括号，修正后333项核对通过，未改动原始结果或受检实现。

## 交付边界与下一决定

主入口见[复现与交付](../docs/19_REPRODUCTION_AND_DELIVERY.md)。两份完整G3训练checkpoint、冻结服务配置、Mac回执、controller回收清单、停止回执与全部失败日志由私有交付索引定位；公开仓库只含代码、原创开发示例、身份、聚合证据和说明。原SFT训练/恢复证据保持，DPO没有checkpoint；G5原始/SFT均0/28、恢复均0/8、L2无官方模型分数不变。

本轮接口、资源和交付材料已通过R1技术终验及Q1实际AI材料审核；全部模型失败与scripted案例身份保持。后续若要改善完整任务成功率，应另立训练/开发协议，验证带最终回答、无需工具和停止决策的监督是否改变上述失败，再使用独立测试；本交付不授权该训练。

## 最终独立接纳

R1技术终验 `a0dd4c3837be938e65ff51101385e0d613b5eb07` 与Q1实际AI材料终验 `e5f16f29b90e8541f12dc0dbe92924864a8af17e` 均PASS。S1分别回读290份、295份私有产物、各两份公开文档及完整独立审计脚本；核对R1的173份当前源码/配置绑定和两方引用的训练制品、真实数组。五组R1只读审计与Q1的实际mask、DPO数学、五类CPU案例、11次真实尝试和原失败说明均支持接纳。复用既有CPU与真实模型运行证据，没有追加模型运行。

Q1登记一项P2 `Q1-G6-DOC-001`：旧候选将五个示例输入笼统写为真实NOT_RUN，而normal输入实际已运行且未完成。`10f99b0`修正后同轮PASS；其余四个不同输入的完整真实案例仍NOT_RUN。修正发生在正式终验签发前，正式未通过次数增量0，原错误及审计失败保留；93项已登记问题均关闭。

G1–G6的阶段验收通过表示实现、运行、证据与交接达到约定范围。G5的M0/M1均0/28、G4无有效偏好及DPO checkpoint、L2无官方模型分数均保持。后续改善完整任务能力，应先在独立train/dev中补充工具观察后的final、无需工具和clarify监督，并验证行为覆盖；现有隐藏测试不能回流训练或调参。
