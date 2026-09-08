# P04数据R3候选CI与限定安装检查

S0；coordination.v1；记录基线 `535cff52cf21f4403952314afd87ea37bf2d9857`。本次仅更新协调与证据，未修改生产代码。R1继续精确 `d80667e4f6e3a63d5c49d4293e99271ca3c2aca1` 的独立CPU复审；F2仍首次正式失败1，尚无新正式verdict。

[Draft PR19](https://github.com/kris0516/ToolAlign/pull/19)候选CI [34171144245](https://github.com/kris0516/ToolAlign/actions/runs/34171144245)双Python全部通过：3.11/3.14各14步骤，默认1,116 passed/48 optional skipped，P00独立46 passed。实际CI checkout `ef244e7d7ed9136d5022c4d57c1efafb26c77d22`，parents为 `6ff0cf72ad309cd7be86a42eb80fee0913a35991`与精确d806候选，tree `57dd5045dd0d34c93a5104eaac3835d1bcb73c67`；664文件与本机Git绑定。证明 `9de6194f45c84ed385c48f7cd979ba4fb878a136a22e3aee83d0d1540672a04e`。这是候选CI，最终集成CI/main未运行；PR18保留旧R2 FAIL及当前处置，PR19保持Draft。

R1回报源码157项、原六项源码检查与独立4项FD检查通过，完整运行证据待最终接收。首个安装版尝试在2026-09-08 00:00:52 UTC退出：wrapper/child均exit1并回收，pytest导入阶段缺少隔离启动器未放行的`py`，fixture runner sentinel97、实际pytest.main未进入、fixture child/fork均0。S0将原回执逐字段绑定原生工具调用，并核验624候选文件、65包文件/76安装文件/75 RECORD记录和pytest自带shim，共727路径，证明 `ebaeaa3c087e56c1b9bf3061e0467503ba7926e09f45e4010f080ae41e54949b`。

该`py.py`为既有pytest 9.0.2自带329B文件，SHA `b71675b5d9845ba0814e9e88767f88dac3b3cc0d3128da028bd45edbb523e871`已绑定pytest RECORD，并只转入已有`_pytest._py.error/path`。S0按[限定追加](../coordination/tasks/P04_SFT_DATA_V3_FD_CLOSE_REVIEW.md)授予同一target、新label及新输出根的一次安装版六项检查；只允许bootstrap放行既有`py`及新记录路由，保留原helper和失败。实际原失败result SHA `627813570b9df6f9ccb1b32110688cdee436282afd0b385dfc0fd78e7f37632f`、stderr SHA `d9070dcebf00124de33eb49a315b083e4cc6db962ce7fd7c5f3b3845739760ac`保持。

本轮S0只读核验助手的两个前置错误分别为安装manifest相对路径未拼target、局部变量覆盖Git输出对象；原错误与修正后通过记录均保留，未触发任何测试/API补跑。新S0构建/安装/依赖/实际数据消费/模型/框架/GPU调用均0；追加检查尚待原生派发与结果。R1整包结论、F2关闭、最终CI/main及正式训练均未登记通过。
