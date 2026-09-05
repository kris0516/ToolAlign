# S0-SHARED-01 / R1 独立证据

日期：2026-09-06；结论：**PASS**；精确 base `4cfbe1a5b8d93c20d7b11ec14b31757a574d0903`；精确 candidate `e4127d9a0e6e30b091cba9b9e22a5fbb7091e9a2`。优先级、边界判断和可合并范围见 [交接单](../../../coordination/handoffs/S0-SHARED-01-review-r1.md)。

本轮沿用同一个独立 R1 任务，审查分支 `review/shared-01-r1`。P00 只作为既有回归测试，没有重新开展其旧问题审查。所有写入仅在自身工作区，跨工作区只读用户明确提供的来源/metadata/日志。

## 实际命令与原始日志

原始 stdout+stderr 在 `.toolalign-local/review-shared-01/logs/`，完整命令/退出码/时间/hash 索引在 `.toolalign-local/review-shared-01/index.jsonl`。表中尖括号仅替换实际命令中的私有路径；不能将它们原样交给 shell。三条 dry-run 使用各自的 `UV_PROJECT_ENVIRONMENT`，位于该私有目录下的 `envs/`，没有创建/修改 S0 环境。

| 命令 | 退出码 / 实测 | 相对日志名 | 原始日志 SHA-256 |
|---|---|---|---|
| `uv sync --locked --python 3.14` | 0；Python 3.14.7，默认环境 | `cpu-sync.log` | `06fb4f251c038a0021dcf77b8205cf4d883c1fcc0f6e5e22fff8deb77a53bdf1` |
| `uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py` | 0；176 passed | `cpu-regression.log` | `722df0f19d16cdb637dd81e2cb465deeb60c997f00d80eadb07bd416f10a27db` |
| `uv run --locked ruff check .` | 0；包含新增脚本 | `lint-review.log` | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `uv run --locked python scripts/check_contract_freeze.py` | 0；冻结 4 files | `freeze.log` | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `uv run --locked python scripts/check_public_content.py` | 0；干净候选 100 paths | `public-candidate.log` | `cdd6afbe67c6d34eb9fd12bf0fcd9bf29cb6d245686663d7fc1fb50577f0e2cd` |
| `uv sync --locked --extra compatibility --python 3.14 --dry-run` | 0；Darwin arm64，计划 50 packages | `compatibility-plan.log` | `b4d95d6e0298e48a664df67e98480b70dc013ded4c935459ed8997a0e370c60c` |
| `uv sync --locked --extra compatibility --python 3.14 --python-platform x86_64-unknown-linux-gnu --dry-run` | 0；计划 13 packages | `linux-plan.log` | `56aa17fd045478d9b4a4b6898e32ea140bd06f26a42d02a920adb0ad2c9ebf35` |
| `uv sync --locked --extra compatibility --python 3.14 --python-platform x86_64-apple-darwin --dry-run` | 0；计划 13 packages | `intel-plan.log` | `5f20bb2286ab9a103a7499c7e8359898ba14a110534bbfaec3fd14c2dc8e3e7c` |
| `uv build` | 0；精确候选构建 | `build.log` | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| `uv run --locked python reports/review/P00/verify_wheel.py` | 0；独立临时 wheel 环境 | `wheel.log` | `3f96f340c368d61c660017289bba9ff17ff591449c8b3abd31e548d0f63e8153` |
| `uv run --locked python reports/review/S0-SHARED-01/verify_dependency_evidence.py --pypi-dir <R1-metadata> --compat-site <S0-site> --s0-verification <S0-evidence>` | 0；只读 metadata/原始证据 | `dependency-evidence.log` | `c60131f9c5c51c2b77c30ffc5c583a904a4e787ba8b482c862b6841b7c0ee444` |
| `uv run --locked python reports/review/S0-SHARED-01/verify_source_evidence.py <D1-source> --revision-api <R1-revision-api>` | 0；明确格式的有界审计 | `source-audit-bounded.log` | `b6e95513587b985c8a939739af485996d1584b7ac2118e465ab630403edbf136` |
| `uv run --locked pytest -q reports/review/S0-SHARED-01/test_boundaries.py` | 0；57 passed | `boundary-probes.log` | `38e04691bc45d8e7843bd91b0b47f7353a3cc63898b1081700b3f1257bd32899` |
| `python3 .toolalign-local/review-shared-01/check_scope.py` | 0；候选范围/祖先/字节核对 | `candidate-scope.log` | `7dac9da6dd203fbbf69980b4aa68630577887f54bff762bba94085ea74314c58` |

默认环境实际为 12 个 distributions；S0 兼容环境只读枚举为 50 个，其四个直接版本、mlx-metal 0.32.2、Python 要求和激活的 metadata 依赖闭包均通过。R1 用自己的 CPU Python 读取 S0 site-packages 的 dist-info，没有启动 S0 的解释器，也未导入 MLX/MLX-LM/Torch。R1 **没有重新安装 ML extra**；该项实际安装证据的执行者是 S0。只读检查还确认其十份原始日志 hash 与 summary.json 相符，未用那些绿色日志代替本轮 CPU/marker/构建验证。

`uv build` 在新增审查文件前对精确 candidate 执行。wheel 检查创建临时 Python 3.14 环境，以 hash 锁定依赖安装 wheel，离开源码目录验证五类 CLI、安装后 schema、依赖闭包及无 ML 后端。新增 packaging probe 另查 wheel METADATA 的 extra 条件。

## 来源与上游元数据

R1 独立获取 [MLX 固定版 JSON](https://pypi.org/pypi/mlx/0.32.2/json)、[MLX-LM 固定版 JSON](https://pypi.org/pypi/mlx-lm/0.31.3/json)、[PyTorch 固定版 JSON](https://pypi.org/pypi/torch/2.14.0/json)、[psutil 固定版 JSON](https://pypi.org/pypi/psutil/7.2.2/json)，使用 `curl --fail --silent --show-error --location` 保存至 R1 私有 metadata 目录，未关闭 TLS 验证。以下摘要属于本次获取字节。

| 固定元数据 | SHA-256 | 与 upstream 核对的锁定制品数 |
|---|---|---:|
| mlx 0.32.2 | `f9a9cbacb8497474da8c5804a1b9c492b77ae0fcffa98efa58dedabe7240776c` | 18 |
| mlx-lm 0.31.3 | `72e18dd10b5f7faf95f7f1773f56049848321e7d3544c2f6630f56228e7eb448` | 2 |
| torch 2.14.0 | `47ee9ad3f56347ac17ee80d0c630af282d170bbeddeb83926a1e5bb432c69629` | 5 |
| psutil 7.2.2 | `84f9d2597c3c15fe19d1ce069bfdbf25951dc423dc51d67c3979468c029b6415` | 21 |

46 项制品 URL/大小/hash/未 yanked 检查通过。许可元数据为 MLX/MLX-LM MIT、psutil BSD-3-Clause、Torch 复合 SPDX；本轮确认候选忠实记录上游声明，不将上游依赖重新许可为仓库 MIT。

ToolACE 文件使用 D1 已有私有副本，**没有重新下载数据**。R1 获取 [固定 revision API](https://huggingface.co/api/datasets/Team-ACE/ToolACE/revision/6bda777c88d21e5a204703c1ee45597a8fa4f734)，确认 revision、gated=false、private=false、来源卡 Apache-2.0 声明；并读取已保存 README。网页工具直接打开固定 README 未返回内容，未把它记作成功证据；实际来源核对依赖已保存 README、新 API 与数据字节。

| 来源证据 | SHA-256 |
|---|---|
| data.json；37,154,735 bytes / 11,300 records | `ba12c083fca7e8da48c67ad5b895e495447da7c66e39a2e19742c082e6cb537e` |
| R1 新读回 revision API | `b0a6e07898b0a9d957a9f8ca1e6f4c8ee418438900401a0e41e05d72bd430b25` |
| D1 schema-catalog.json | `9b15cae59673c2b036766fed6b83c9a1e75fa1dda0b10e0f2aeabcdc56764c34` |
| D1 annotation-examples.json | `f16a06a417bfcbff29b63d12c82d02a1c44fa964c0d3e89e19b89ccf5991eb07` |

`verify_source_evidence.py` 是只读统计/样例核对脚本，**不产出 normalized example，也不是 normalizer**。它只识别明确的英文 JSON 工具列表头及非空合法工具声明。R1 对该口径得到 10,534 个记录/33,690 次工具/120,900 节点，后两个计数与 D1 相同；D1 的 10,782 个“可解析记录”口径另外保留，没有用它估计留存率。

实际核对到 default 11,213、pattern 1,336、format 418、examples 59；boolean:string 68、float:string 373、int:string 63 合计 504 个指定类型冲突。它们只是冲突类别的一部分，其他 null/boolean/number 冲突同样须按政策处理。12 个 annotation 示例与原数据对应 schema 逐字段相同。源索引 36/300/1458 的三种字符串 default 冲突，5/360/1779 的 format/pattern/examples 代表形状已进入边界判断；公开文件仅保留索引/类别/摘要，未复制原始 schema、对话或训练数据。

## 审查脚本的初次错误

以下均是本轮新增只读审查脚本开发过程，未改候选或原有测试来消除失败。原始失败日志保留；最终有界统计的通过不表示 D1 全量格式解析已经验收。

| 日志 | 退出码 | 原因 | SHA-256 |
| `source-audit.log` | 1 | Counter.update 误传 dict 值而非 keys，统计脚本 TypeError；改为 node.keys() | `83e15ff52fb07f0a7dc113bec72ab6a70ff0581559afccfa406c7d58b4f4ba27` |
| `source-audit-final.log` | 1 | 以第一个 JSON 列表作为工具声明，得到 10,877 个记录，与 D1 口径不一致 | `b158cfb843928e0adfd50ce72e92c2eb74367066b8a6df77eaf5cb4a38f2cf02` |
| `source-audit-verified.log` | 1 | 增加工具形状检查后仍为 10,816；识别范围未限定，仍无法对齐 D1 全量记录口径 | `0d03b48ec47a4423d968f6e4a596adbab5bbd615097a921424ca2fddfd958c0a` |

最终版本明确限定英文 JSON 工具列表头和非空声明，区分 R1 有界抽查与 D1 原始汇总。它验证来源身份、前 32 条 142 个工具、真实负例形状和 12 条对应 annotation；没有通过修改 D1 统计、放宽冻结 validator 或伪造格式成功来获得 PASS。

## 新增探针与产物摘要

57 项探针包含：40 组 Python/平台/extra 的直接 marker 和传递锁依赖图，四个精确 pin/原 CPU 依赖不漂移、制品官方来源/hash、wheel extra metadata、政策外壳可通过冻结契约、五类源关键词不能原样进入 wire、五组 typed default/省略参数行为、三个已有/收窄边界。Windows/Linux ARM 等只作静态 marker 检查，未声称实机支持；policy probes 检查冻结边界，不执行尚未实现的 D1 转换器。

| 对象 | SHA-256 |
|---|---|
| 精确 candidate diff | `f3bb70665a0e939dfe400c6f73ad48a5f65983a34c92eeda500c7576969312b5` |
| pyproject.toml | `7fe9bca22f4e49825a40ec8b43325d8119693c6ce657be061a186e7796d0f198` |
| uv.lock | `54042e7a1922834e160b31a8cae14d36ab6534ca29615f932cdcee9406fdcebc` |
| source_toolace.v1.json / policy hash | `b8c4cd238bbf27d3378dadcd4130ac44c4c991ace6315bf385f104c4f98f72f7` |
| docs/13_TOOLACE_SOURCE_POLICY.md | `3f528fa7845e14583a6c6eb9809469bf44518675ee3d8faf3136ffb3d92a74aa` |
| candidate wheel | `b2e4f5b81d63721e248e066476432b524939bd82a0214b586f53b21c15edcb98` |
| test_boundaries.py | `8a5b176def3d660a049d23a12c824418e999bc8da4da0fa8b249eea46f86f9f0` |
| verify_dependency_evidence.py | `199d8afc75a0eec961a29711fde9a2d3b751a8d97d215ab00233c280507f146c` |
| verify_source_evidence.py | `7181f33658fe61a6d3ea72a8734df31d8d728cad540d0a5a63f5350e7977e803` |

原始日志 hash 仅用于证据关联，不能单独证明结果正确。公开目录仅含本说明和三个审查脚本；真实任务身份、路径、源数据及大日志不提交。剩余 P0/P1/P2 均为 0；CI/main 集成、P01 后端与模型、P02 转换/质量、P03 执行边界均不因本报告通过而变成已验收。

提交前再次扫描实际 index 与工作副本：`uv run --locked python scripts/check_public_content.py` 退出 0，105 paths；`public-staged.log` SHA-256 为 `7cd8f290b19fb66f028f2f7d130d1e5214a561e416fca9b4691a501e0d3b26b4`。私有提交检查脚本确认仅五个允许新增文件、工作副本与 index 一致、没有其他改动和私有身份泄入暂存区；退出 0，`submission-audit.log` SHA-256 为 `c995742ab7625bc1944dbcc0668fd833ad51d9880efeb2e993667b10ba5168b5`。
