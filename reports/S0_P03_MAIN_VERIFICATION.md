# P03｜S0 主分支集成验证

2026-09-06；S0。**P03 VERIFIED，范围为本地 CPU 工具执行器、独立语义 oracle 和 scripted ModelBackend。** 已完成精确候选独立复审、最终 CI、普通合并及实际 main 验证。真实模型 backend 和正式评测属于 P04/P06，本报告未授予其验收。

## 精确提交与审查保全

- [PR #7](https://github.com/kris0516/ToolAlign/pull/7)已读回 closed/merged；实际 main 合并为 `29a5e4c6affa2b822717fd3184b25ccb756e1651`。
- 完整被审候选为 `3598cef2efb99e2990e384812a028902964cf494`；R1-r2 PASS，P0/P1/P2 均 0；[原始审查交接](../coordination/handoffs/P03-review-r2.md)提交 `a78071bf6ac40f2729e090e1828a1c6022cd8d00`，直接以该候选为父，只新增 6 个审查文件，158 份被审文件不变。
- S0 完整读取复审报告、原创反例及审计/安装脚本，实际核对 139 项日志、结果、安装输出、源码和归档 hash。原 F1/F2 收尾异常与 F3 事件因果问题均关闭；原 `f34f7c5` 的 FAIL、checkpoint 和开发失败保持原 SHA 与证据。
- S0 普通 merge 当前协调 main 和原始 review，形成最终 PR head `84084770bf07f32647af36ac748bf76326e74ed1`。49 个既有受保护路径和 38 个 P03 实现/测试/证据路径保持对应来源字节；完整变更为 37 个路径，未修改被审实现。
- [最终 CI 34014772645](https://github.com/kris0516/ToolAlign/actions/runs/34014772645)的 Python 3.11/3.14 jobs `101436547162` / `101436547295` 所有步骤成功。实际 main tree 与最终 CI head 完全相同，均为 `1873d450c746abe642a746194d384eb93357c4be`。

## 实际 main 验证

2026-09-06 05:50–06:01 UTC，macOS arm64、Python 3.14.7，纯 CPU、离线。复用已核对的 28 包固定 CPU 环境，包含 tokenizers 0.22.2 和 psutil 7.2.2；真实 tokenizer 输入三个小文件 hash 已绑定，模型框架不可导入。完整 argv、时间、退出码、stdout/stderr 和私有驱动保留本机。

| 实际检查 | 退出码与范围 | 原始日志 SHA-256 |
|---|---|---|
| 首次完整 CPU 组合 | 1；550 passed / 1 failed，原因见下段 | `9cc22832c873b4e686af0b6e7f45ec79ffeb60f02db36d49d5fd0c868f04c5c3` |
| 修正临时目录后的完整 CPU 组合 | 0；**551 passed，0 skipped**，40.55s | `ec351c5911b6fb8aaab8f0101633a141270b401b3f929e6f94325ed9510226ba` |
| 当前 CPU 环境/来源核对 | 0；28 包固定版本及 tokenizer hash 一致 | `9caff7dfd0255c6119b98a7796d47530ed3af18fbac4c3ddbb66b6d16d96f81b` |
| `uv run --offline --locked ruff check .` | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `scripts/check_contract_freeze.py` | 0；冻结清单保持 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `scripts/check_public_content.py` | 0；213 个追踪路径 | `84ddf806f1679951020cbbf724f328a4f0234a88c22919b6b32d4d7482253b68` |
| 正常 `uv build --offline` | 0；实际 sdist 及由其生成的默认 wheel | `25f3349feec6eeb11d33e542d75770fd53079d02fcb86db79421c5a8e3a021b0` |
| 从实际 sdist 显式重建 wheel | 0 | `c872d50600483ac14fc29745ad2308dd5b4d3dc31c2cbc8a4a577f7a206e56bf` |
| 三份归档实际成员/字节核对 | 0；无未知载荷或源码差异 | `e60a80e02fe5e74c585d8967ac59536d4fed3d569ef5d8d03ff585fb4816cee9` |
| 新隔离安装及组合接口 | 0；18 条子命令全部退出 0 | `7f8642807a7752004e01328dd2657ccf92e0f27335eb296db7b6bd5604b5dc29` |
| 新 demo 制品及资源/人审状态核对 | 0；计数与 hash 一致 | `54dd45fcd5a0e5a4fb6e4835b89c3fbfa2fa18885650c78e739c2a2588ba7e8c` |

首跑时 S0 把 pytest basetemp 放在 `.toolalign-local` 下，导致 P02 的“公开输出目录”负例也继承私有祖先目录；实际实现正确识别其为私有，原测试因此失败。S0 仅把 basetemp 改至独立系统临时目录，原实现与原测试均未改；第二次完整组合全部通过。首跑日志保留，不将其描述成候选修复或删去失败。

551 = 已验证 P02 组合的 338 项 + P03 新增 213 项；不重复累计历史结果。核心命令如下，环境与临时目录实际值在私有证据中绑定；临时目录不能处于 `.toolalign-local` 之下。

```bash
PYTHONPATH=src TOOLALIGN_TOKENIZER_DIR="$TOOLALIGN_TOKENIZER_DIR" "$S0_CPU_PYTHON" -m pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py reports/review/P02/test_p02_boundaries.py reports/review/P03/test_p03_lifecycle.py reports/review/P03/test_p03_semantics.py --basetemp="$S0_PYTEST_TEMP"
```

原 R1 的 54 项反例包含在此组合；R1-r2 新增 31 项通过安装后的包再次运行，**属于已有独立检查的安装路径复验，不新增独立检查计数**。其范围包括真实进入 generate 的收尾写入/目录故障、原始 parse_failure 与预算保全、合法和不可靠因果 trace，以及正常、timeout/cancel 和无关进程对照。

## 实际包与隔离行为

| 产物 | Bytes / 成员数 | 实际来源与内容核对 | SHA-256 |
|---|---|---|---|
| sdist | 165421 / 76 | 75 个 Git 追踪文件逐字节一致 + PKG-INFO | `dc8570f51e38e877f535afa89e2e11f22ac7a3d6cdd640d77d94f0a7c45912a4` |
| 默认 build wheel | 70311 / 39 | 同次 sdist 生成；34 个源码/资源 + 5 个 metadata | `ae818c02c40e6677373e4315c6e87cd559c1ebe435a521ad7ad53c3cd1259d96` |
| 显式 rebuilt wheel | 70311 / 39 | 另从上述实际 sdist 重建，与默认 wheel 完全一致 | `ae818c02c40e6677373e4315c6e87cd559c1ebe435a521ad7ad53c3cd1259d96` |

三份归档均按实际当前 Git 字节核对，无未追踪载荷、缺失预期文件、重复/链接/逃逸成员或源码差异。本次正常包没有额外执行源码直接 wheel 构建，该路线为 NOT_RUN；未变共享归档边界脚本的多路线探针已在上述最终双 Python CI 通过，S0 本地未无理由重跑该调查。

新隔离环境按锁文件导出默认依赖并要求 hash，离线安装后以 `--no-deps` 安装 rebuilt wheel；清除 PYTHONPATH/PYTHONHOME，从源码目录之外以 `python -I` 执行。18 条命令的 36 份 stdout/stderr 已逐项绑定。

- 契约 digest、五类 fixture、数据与工具 CLI、registry 通过；实际安装的 34 个源码/资源与 Git 字节一致，未从工作树导入生产模块。
- 原 P02 两次构建的 18 项制品重新比较一致，data-build manifest 仍为 `87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`。
- 原创小输入实际经过安装后的 P02 转换和 P03 raw Action parser 往返；typed default 未补入真实参数，历史未绑定工具被 registry 拒绝为 unknown_tool，未执行数据来源工具。
- 新 installed scripted demo 为 10/10，六类工具及无需工具、澄清、多步依赖、故障恢复均包含；90 条 trace、20 次模型决策、10 次工具轮次、20 个自有进程及 20 个回收记录完整。220/140 tokens 为合成测试计数，不能解释为真实 tokenizer 吞吐或模型分数。
- 31 项 R1-r2 原创边界在安装路径再次通过。真实阻塞/自有进程生命周期的证明来自实际探针；事后读取历史 PID 记录不被当作当前存活检查。

## 证据索引与后续门槛

私有机器摘要 SHA-256 为 `1adf8846e607e3191e847e0358ef314d7df71a8cdf32ca39864a9ea3b97cc8da`；归档 inventory 为 `b31c54af47666ce91e9c34d76a4a385839b1261414215472a7db8487e21f5b5e`；隔离摘要为 `ee16a839c25699c2fa64dd908aba853cba47715d4a1581067c2d0db98097062e`。摘要绑定全部 11 条实际命令、独立环境、最终 CI、main 读回及验证驱动，旧失败和所有原始审查保持。

05:59:42 UTC 实际共享 GPU 租约为空闲；P02 人审填写副本仍为 100 行、0 verdict / 0 reviewer，hash 与原空表相同。本次没有填写人工判断或改变原数据。P02/G-DATA 仍待 kris 语义审查和训练配置绑定；P01 仍待其独立复审/集成，共同格式按 ADR-0017 实现中。真实 MLX/Qwen backend、正式训练、BFCL/隐藏集、推理服务均 NOT_RUN；无新增 GPU 作业、费用、模型/数据上传或公网服务。
