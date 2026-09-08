# S0｜v3数据FD修订独立审查接收

状态：ACCEPTED（CPU技术），待组合、最终CI/main。R1对精确candidate `d80667e4f6e3a63d5c49d4293e99271ca3c2aca1`正式PASS，P0/P1/P2均0；原review `f2f11e04a94cebb0ad658851d4e22a8452180556`，tree `95ff7bba5e15e3fed71a822c9eaf65567e3c1a65`，唯一parent为d806。2026-09-08 00:23:00 UTC原生completed/idle；普通推送远端一致，工作区干净。

S0于00:28:02 UTC完成96,720当前路径、1,774链接、21个仅lstat特殊节点及29条原生命令/独立终态关闭器核验，证明 `5ad348fdd040b1228077f842d0008e437c254cb59ac4aa683e8770c99ac2f764`。628公开文件与Git绑定，624候选逐字不变，只新增4份允许的审查材料，精确公开副本已保存。原seal `9ed0f6228650b58eb3fcab6ae7c44402326e21bf4ef14258dc6f7ce0bd59a586`、envelope `d842ba8631412fdf8e4c4da8feb2711d1c391ee7395b168e3c84ddce2450008d`保持。R1记录的97,329路径包含历史公开别名；S0通过已绑定Git/现存快照核验并按实际路径去重，不以新checkout冒充旧源码。

实际一次157模块、原六项源码6、新独立FD组4及限定安装六项6全部通过。新4项证明SystemExit构造失败时同一自有FD关闭且原异常保持；stream成功/摘要拒绝/部分读取失败后的同FD编号新owner均保持打开，部分读取实际1MiB，不二次关闭已移交FD。8个实际fixture child均exit0/reaped，并核验已不存在。5个测试启动中首次安装启动为exit1、pytest.main/用例/fixture child为0，其reservation已消费；其余4次成功与原失败分别保留。

原安装启动器缺少pytest既有py shim；75e03f6追加仅在新副本增加该顶层模块放行与新文件/label/child路由，S0逐字比较确认。仍同一现存target、-B/-I/-S、外部cwd和精确来源，没有导入预演或第二次安装。三现存归档143/70/70成员、65包/76安装文件/75 RECORD/32模块来源通过；无新增归档构建、依赖、环境或下载。

29条原命令中4条exit1完整保留：两个preservation助手错误、首intake字段错误、首次安装启动错误；另4次只读查看错误保持。这些不是候选正式失败轮次。原30文件/1链接缺失例外未恢复冒充原件，20模型文件仅stat复核；旧f708不在公开祖先。新增证据151,833,869B，低于1GiB。

S0据精确独立PASS关闭 `P04-SFT-DATA-V3-F2`，连续失败1→0；原58212d2/1769046 FAIL及原F1历史均保留。84项登记问题全部关闭，未触发第五次规则；[台账](../coordination/REVIEW_FAILURES.json)。这不改写旧语义FAIL/UNKNOWN或此前运行时点。

下一步由S0隔离普通整合最新main、原候选及三轮原review，运行一次默认CPU组合检查与相关独立fixture，构建一组全组合sdist/direct wheel/rebuilt wheel并离线安装一次新target。组合同时包含已验收模型模块和新数据模块，旧单包归档不能代替该组合实物。随后最终双Python CI、普通合并PR19和main验证。新增固定609 prepare/verify、13材料转换/导出/回读、编码、模型/框架/GPU/优化/生成仍0；本次d806真实消费NOT_RUN，原消费保持1769046时点。

CPU运行配置fa9e52b4已冻结但任务仍PLANNED，等待数据主干验收才派发。完整P04训练、容量、正式评测与服务尚未验收；S0本次仅接收证据，未新增测试/API/build/install/model调用。
