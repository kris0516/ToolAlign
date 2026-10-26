# S1｜首次 Colab 实装与失败回收

**两次 setup 失败已完整回收，索引修复通过独立 CPU 复核；新实例实装待执行。** 首个 L4 已停止，系统缺 `python3.12-venv` 已补齐，pip 丢失 CUDA 附加源的原因与修正见下文。真实容量和恢复训练尚未执行。

执行源码为已合并 `920c41551f0f7f2be8a5a8dcced23cc080ac1f27`，Linux锁 SHA256 `14e8724b9d78e7bcabc270aa2c0cfe05ea5a5d855fffda08dad7aa0a93c20fb4`。Q1实际20例审核 `ed022dae68c516727ec4cdbc91a09ce050a50338` 已通过。

| 实测 | 结果 |
|---|---|
| 硬件 | NVIDIA L4，23034 MiB；驱动580.82.07；主机约53 GiB，无既有GPU计算进程 |
| setup r1 | Python3.12创建venv失败：ensurepip不可用；未安装训练依赖 |
| 系统前置修复 | 安装实际候选python3.12-venv=3.12.3-1ubuntu0.17，exit 0；ensurepip报告pip24.0 |
| setup r2 | pip24.0无法找到torch==2.8.0+cu128；最终专用环境中仅pip，未加载模型 |
| 根因 | 真实handle_option_line读取index-url时以单元素列表替换全部索引；直接CUDA源查询包含所需版本 |
| 回收与停止 | 两个run分别完整4文件回收并逐项校验；stop核对两份当前副本后停止，回读会话不存在 |

第一实例从申请到确认停止669.429秒（11.16分钟），包含准备、失败与传输。账户余额查询差值为0.23 CU，停止后费率0、活动分配0。无新模型下载、真实模型加载、数据上传、forward/backward或optimizer更新。实例内隔离的半成品环境属于临时缓存；持久保留的是Mac上的完整run文件和诊断记录。

有界三步容量配置未被执行，单次600秒、累计3步、输出512MiB及预设恢复比较容差继续适用。后续依[修复任务](../coordination/tasks/P04_COLAB_ENVIRONMENT_R4.md)与[独立复核](../coordination/tasks/P04_COLAB_REVIEW_R4.md)推进；总分配5400秒、既有8CU上限包含本次消耗，新的实际分配预算需扣除已用时间。正式SFT和模型效果仍NOT_RUN。

| 实际记录器回执 | SHA256 |
|---|---|
| setup-a-command | `73acce02039324a602568cf8675ae218dc1b741e512b1c63a79f9e3c7ee43f07` |
| setup-a-r2-command | `7f3b4a893895ce30e4c4db86ae99adb32379a11a51f7c3b231d6fd30f6944e43` |
| diagnose-index-command | `8fde76812e862001c0778a9592eccffafbc583dd17c30813390816dc8966d4cd` |
| recover-setup-failure-command | `4c9f0877d538462466b2db95e9f0443d579ca3f6afd42113ac0370eb562c3ba8` |
| recover-setup-r2-command | `bc74b0f20a6c37b9bd472b5b161b186ec6ae48edf2a8598c6902291552f6dc70` |
| stop-a-command | `d64b75cc4de0bcbf93e9fa460ffb957e6373e91879bf7ce25cf8b503e2ff551e` |

所有上述命令均有原始stdout/stderr；记录器源码前后不变。两次setup的exit为1，其余诊断、回收和停止为0。稳定问题ID为`P04-COLAB-INDEX-001`；首次登记为S1运行发现；随后独立PASS见下节，不按r4任务名累计失败次数。

## 索引修复的独立与集成验收

E1最终候选 `99b8116ad985c999f3cf4fb3c918eeadf50f8814`（实现 `2ecb7a8b1ca73386f68d79d34896a3aedeb2658e`）只修改索引头部、相关回归及说明。独立R1提交 `c4b5c1c26c4385c3828c986875f9ccebf806f542` 给出PASS、P0/P1/P2均0；真实pip24探针修前丢失CUDA源、修后保留两源，48个pins及894条hash未变，建议关闭INDEX-001。

S1在组合 `75cd7fbc95da496fe9653b15125fe576cce4fde6` 上实际执行两项新pip24回归：2 passed / 0 skipped，wall 1.256秒、source_unchanged=true；回执SHA256 `d83650ff896f5a914a1a2ad5ca9185b2e9c482fc9cd87ae84f12334a477fabc5`。未重复未变的数值/数据/进程检查。新锁SHA256为 `6a793bfd46af168b2df581f19ce8f23f97af239a12ac95b436e99baff080b2ea`；这些CPU证据不替代新实例实装和CUDA运行。
