# S0｜v3 数据与固定模型 CPU 组合验证

结论：PASS（隔离组合）；最终 PR19 CI 和 main 验证待完成。2026-09-08 00:51:47 UTC，S0 封存证明 SHA `04fc2a58e365f03a3b391451a05b5d2a465e8862319a6576320c52bc515f1d52`。实际核验 3,399 份文件、218 个链接、7 个仅 lstat 的 FIFO，新增封存前常规制品 110,903,775B。

从已验证模型主干后的协调基线 `40974f3e1ad1d6cca4d4d7d917487bcd7af3008f` 普通合并数据候选 `d80667e4f6e3a63d5c49d4293e99271ca3c2aca1` 和原 R1 PASS `f2f11e04a94cebb0ad658851d4e22a8452180556`，再保留原两轮 FAIL 提交 `b99a644e3ac0386f5ebe55cfd32e51b99e89781a`、`58212d26bdb1c6a681a1ac34ccae854daefca8d3`，得到组合提交 `3a5c90803be5b750773bb46b04101b7de83466a2`。682 份公开文件均与 Git blob 及命令首尾字节一致；657 份基线文件保持，25 份数据实现/交接/原审查文件加入，无 S0 生产代码改写。独立接收及 F2 关闭依据见[原 R3 接收](S0_P04_DATA_V3_REVIEW_R3_HANDOFF.md)。

本次组合 CPU 原命令结果为 **1,135 passed / 1 failed / 48 skipped**。唯一失败是 `test_private_output_path_and_symlink_ancestors`：S0 的初始隔离 checkout 位于私有目录祖先内，测试构造的“公开”路径实际仍属私有；生产函数据此允许导出，与测试预期不符。原失败、完整输出和两份 fixture 文件均保留。S0 在无该祖先的独占 checkout 上，以同一精确组合提交仅重查该一项，**1 passed**；原 1,135 项成功没有因目录变更重跑。两次结果覆盖 1,136 个通过的唯一用例，不能描述为一次全绿运行。48 项可选环境检查按实际默认环境跳过；没有导入 MLX/Torch 或补装 psutil。

实际命令使用既有默认 Python 3.14.7 / pytest 9.0.2，禁用插件自动加载、字节码及共享 pytest 临时根。命令形式与范围如下；所有绝对私有目录、原 argv/UTC/exit、源码时点和 stdout/stderr 均仅存本机封存。

```text
python -B CPU_RUNNER -q -p no:cacheprovider tests \
  reports/review/P04-qwen-model-r1/test_independent.py \
  reports/review/P04-sft-data-v3-r3/test_independent_io.py \
  --basetemp=EXCLUSIVE_ROOT --junitxml=RAW_XML
python -B CPU_RUNNER -q -p no:cacheprovider \
  tests/training/test_sft_data_v3.py::test_private_output_path_and_symlink_ancestors \
  --basetemp=NEW_EXCLUSIVE_ROOT --junitxml=SUPPLEMENT_XML
ruff check .
python -B scripts/check_contract_freeze.py
python -B scripts/check_public_content.py
git diff --check
```

三份组合归档已实际离线构建一次：sdist 147 成员、源码直接 wheel 71 成员、从该 sdist 重建的 wheel 71 成员。146 份打包源码/测试/配置字节绑定当前 Git；两 wheel 全部成员一致，66 个生产包文件、全部 RECORD、metadata、entry points 和 LICENSE 通过，未追踪/私有载荷为 0。使用已核验的既有 Hatchling 环境，未新建环境或安装构建依赖。归档证明 SHA `e1dcc04511aeeea26ddeee168baa61f866a1a970d03a8dd2e7cd3b86bbc4b378`。

```text
uv build --offline --no-python-downloads --no-build-isolation --python EXISTING_BUILD_PYTHON --sdist --out-dir SDIST
uv build --offline --no-python-downloads --no-build-isolation --python EXISTING_BUILD_PYTHON --wheel --out-dir DIRECT
uv build --offline --no-python-downloads --no-build-isolation --python EXISTING_BUILD_PYTHON --wheel SDIST_FILE --out-dir REBUILT
uv pip install --offline --no-python-downloads --no-deps --python DEFAULT_PYTHON --target NEW_TARGET DIRECT_WHEEL
DEFAULT_PYTHON -B -I -S INSTALLED_BOOTSTRAP parent
```

一次新默认 target 安装含 77 文件、76 RECORD 行及 66 个生产文件，均绑定本次直接 wheel 与源码。外部 cwd 的 `-B -I -S` 父进程和三个子进程使用安装目录；35 个父进程生产模块来源全部通过，无源码 fallback。原未修改六项 I/O 检查安装版 **6 passed**，三个子进程 exit0/reaped，S0 另用 ps 确认全部已消失。固定模型 `load_qwen_model` 的一次缺租约调用在文件/配置读取前拒绝 `active_current_gpu0_lease_required`；不读取真实模型文件。

共 11 条执行命令保留原始回执，初始 CPU 命令 exit1、其他十条 exit0。新增三份归档和一次 target 安装如实计数；真实609数据 prepare/verify、13材料转换/导出/回读、编码、框架、模型、优化、生成、GPU、容量及正式训练新增均为0。旧固定消费仍在原1769046时点；d806真实消费保持NOT_RUN。84问题关闭记录保持；没有新增正式修订失败或运行授权。
