# P01-base-r2｜共享基线 CPU 同步证据

2026-09-06，T1 自测同步交付，待 P01 独立 R1/S0 验收。本轮只接入已验收的 S0-SHARED-02，检查依赖元数据、CPU 数学参考和发行包；没有重新运行模型实验。

## 提交关系与不变范围

| 角色 | 精确提交 |
|---|---|
| 保留的 P01-r1 完整候选 | `f97bb0de346c220871962a5689014a379fe19c83` |
| 新生产 code_base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| S0 本轮 authorization_commit | `f2a271be616cdb53c01e8d671029f31ae140c037` |
| T1 原分支的非强制合并 | `17a003f2678682fd3c6a072eba2b105fafc87102` |
| 本轮 CPU 审计脚本提交 | `e6825f657a359a812b44b8db96d7929efd9f77ff` |

分支仍为 `work/p01-compatibility`。无 reset/rebase、无丢弃旧候选、无冲突；未修改其他 worktree 或全局 Git 配置。契约仍为 `plan-v0.1 / coordination.v1 / toolalign.contracts.v1`，模型设置仍为 `gpt-6-astra / max`。

合入前已按授权读取 AGENTS、GOAL、PROTOCOL、任务包新增基线段、PROJECT_STATUS、[S0 主干验证](../S0_SHARED_02_MAIN_VERIFICATION.md)和[新环境说明](../../docs/15_P01_ENVIRONMENT_AND_SOURCE_PACKAGES.md)。公共配置与协调文件变更全部来自该 S0 merge；T1 新增文件限 `reports/hardware/P01_BASE_R2_*` 和本轮交接单。

逐文件与旧候选对照：P01 的 8 个实现文件、2 个测试文件、10 个旧硬件证据文件及旧 P01-r1 交接单，共 21 个文件字节全部未变。**SFT/DPO/GPU 入口、mask、reference、数值门槛、保存重载和资源监控路径没有改动。** 具体 SHA-256 在 [元数据与制品核对](P01_BASE_R2_METADATA.json) 的 `preserved_previous_files`。

旧 10 次运行的 manifest 制品 path/size/hash 再次验证，重建汇总与旧 [P01_RESULTS.json](P01_RESULTS.json) 字节完全相同，SHA-256 `d0fb9deb067b1e3f6f8b85855a0d1509b3bc15569065bbfed22a5c95928f42bd`。旧配置、失败首选/备选、资源停止、原始日志与校准结果保留；新检查输出写入独立私有目录。

## 适用 CPU 与包构建

[P01_BASE_R2_VALIDATION.json](P01_BASE_R2_VALIDATION.json) 保存真实命令、UTC、退出码和完整原始日志 SHA-256；原始日志仅在本 worktree 私有 `checks/base-r2-*`。

| 检查 | 实际结果 |
|---|---|
| `uv sync --locked --python 3.14` | 退出0；默认 CPU 环境 |
| `pytest -q tests` 加 P00 首轮和 P00-r2 独立审查测试 | **217 通过** = 58 原基础 + 41 P01 + 46 P00 首轮 + 72 P00-r2 |
| ruff / 契约冻结 / 公开内容扫描 | 退出0 |
| 原 P01 sdist 只读枚举 | 退出0；当前选择45文件、373,065bytes，私有文件0 |
| 公共真实归档回归 | 退出0；241私有canary被排除，18公开对照和冻结schema保留；sdist、直接wheel、由sdist重建wheel均检查 |
| 原 R1-r3 附加边界探针 | 退出0；45私有/21公开边界，泄漏0，原脚本未改 |
| 正常 `uv build` | 退出0；真实构建sdist，再从该sdist构建wheel |
| 原 P00 wheel 隔离安装验证 | 退出0；CPU依赖闭包/hash、脱离源码导入、五类契约CLI及无ML后端导入通过 |

217 与旧 P01-r1 的 274 口径不同：旧数包含 S0-SHARED-01 的57项历史快照，该快照断言“仅一个extra”，不适用于合法新增的dpo/p01-replay组。没有修改旧断言、没有把它们记为当前通过；本轮采用共享02的实际适用验证。归档canary数不与pytest数相加为覆盖率。

本分支实际产物逐项与Git追踪文件核对，未跟踪payload为0：

| 制品 | bytes | 文件/追踪文件字节相同 | SHA-256 |
|---|---:|---:|---|
| `toolalign-0.0.1.tar.gz` | 110,865 | 47 / 46；另1项PKG-INFO | `f74cd964bec2af10f673ac5104a88b9162a7cd27fb4a5e6398a9be621424c508` |
| `toolalign-0.0.1-py3-none-any.whl` | 44,037 | 27 / 22；另5项dist-info | `043e5d4508704d5637f7a9fef20dcb236c5223649def73b832750fa94dabd69b` |

P01实现进入当前包，故大小与只含基础实现的S0主干包不同。新报告和历史研究证据按公共规则不进入sdist；仍在Git/受控私有证据中交接。旧wheel在本机私有目录留存，本轮没有发行或上传任何归档。旧sdist失败记录没有被改写。

## 新可选环境与实测清单对照

在本 worktree 的两个新私有venv中分别执行：

```bash
UV_PROJECT_ENVIRONMENT=.toolalign-local/base-r2/venv-dpo uv sync --locked --python 3.14 --extra compatibility --extra dpo
UV_PROJECT_ENVIRONMENT=.toolalign-local/base-r2/venv-replay uv sync --locked --python 3.14 --extra compatibility --extra dpo --extra p01-replay
```

安装与metadata审计没有导入MLX或模型库。原独立 `verify_dependencies.py` 核对所有93条lock记录的registry/制品hash、默认11条第三方锁记录不变、已装metadata与当前平台locked export完全一致、wheel三个extra及Darwin arm64 markers，并检查跨平台导出。跨平台仅解析，不是实机训练验证。

| 已装环境 | 总distributions（含项目） | runtime闭包 | dev-only | 与旧88包探索清单的真实差异 |
|---|---:|---:|---:|---|
| compatibility+dpo | 69 | 64 | 4 | runtime已有包版本相同；少21个完整replay依赖；新增ruff和项目自身 |
| compatibility+dpo+p01-replay | 90 | 85 | 4 | 旧88包全部同版本；新增ruff和项目自身 |

dev-only按实际metadata依赖图求差，为 `iniconfig==2.3.0`、`pluggy==1.6.0`、`pytest==9.0.2`、`ruff==0.15.0`；`toolalign==0.0.1`另列。pygments等也被runtime依赖，未误列为dev-only。旧探索清单已包含前三个dev包，未包含ruff和项目安装记录。完整逐包runtime版本、缺少的21项和差异见元数据JSON。

关键版本仍为MLX/Metal0.32.2、MLX-LM0.31.3、Torch2.14.0、备选mlx-lm-lora3.1.2、首选审计mlx-tune0.6.0、datasets3.6.0、dill0.3.8、fsspec2025.3.0、multiprocess0.70.16、transformers5.16.1。相对旧公共shared01，fsspec确实由2026.7.0变为2025.3.0；相对T1模型**实测**环境没有runtime版本漂移。三个候选库共11个已记录关键源码文件SHA-256与原探索记录相同。

组职责未改变：完整P01 math/smoke/calibrate仍包含mlx-tune负例与跨库审计，必须选择p01-replay；这不表示首选DPO通过。metadata MIT与随包Apache-2.0 LICENSE不一致的mlx-lm-lora许可事实继续保留；公共文档已登记，不由T1替上游裁决或重标许可。

## 本轮 PyTorch CPU 参考

新replay锁环境只运行 [P01_BASE_R2_TORCH_CPU.py](P01_BASE_R2_TORCH_CPU.py)，调用原实现中两个PyTorch参考函数。脚本禁止MLX、MLX-LM、mlx-tune、mlx-lm-lora与transformers导入；只分配小型float32 CPU张量、最多2个CPU线程，不创建模型、不取GPU租约。用stdlib标量log-sum-exp和解析梯度独立比对，也核对旧math-r2已记录值。

| 检查 | 实测 |
|---|---:|
| CE / DPO loss | 1.9298582077 / 0.6867220998 |
| CE与独立标量 / 最大梯度误差 | 7.6996e-8 / 5.4290e-9 |
| DPO与独立标量 / 最大梯度误差 | 3.2096e-8 / 8.6923e-10 |
| 初始ln2绝对误差 | 1.9047e-9 |
| 对旧math-r2 MLX记录的CE / DPO差 | 1.1921e-7 / 5.9605e-8 |

所有误差小于2e-6；忽略位置logits扰动不改变CE，reference没有梯度。此处与旧MLX值作离线比对，**没有重新执行MLX/PyTorch完整数学探针**，更没有把新环境安装当GPU兼容验收。

## NOT_RUN 与下一门槛

本轮MLX导入、模型加载、GPU校准、完整math重放、0.6B/1.7B重跑均NOT_RUN；未重复未受影响的104可测微步实验。历史最多32新token的小生成仍不等于256token/30秒完整harness，P03集成推理/正式P04/P05/最终测试/BFCL/服务部署均未授权或未运行。独立P01验收与kris人工语义确认仍待完成。

本轮交接：[P01-base-r2](../../coordination/handoffs/P01-base-r2.md)。最终包含本报告的完整候选SHA由原生交接消息给S0；S0调度R1审核后才能集成，T1交付后停止等待，不自行合并main或创建新任务。
