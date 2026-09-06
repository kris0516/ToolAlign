# P02｜S0 主分支技术集成验证

2026-09-06；S0。**主分支技术验证 PASS；P02 状态为 MERGED，整包与 G-DATA 仍待人工语义审查及训练配置绑定。** 本报告不授予训练、正式评测或服务部署验收。

## 精确提交与独立审查

- [PR #5](https://github.com/kris0516/ToolAlign/pull/5)已读回 closed/merged；实际 main 合并：`2ec17673c18ffbc817b1ff8512e53e44a11766a5`。
- 最终 PR head：`71a50ba4981c417da37013f9b5c69a2cc3635d05`；其 tree 与实际 main 均为 `c1951de570f6c76593a1e5da7c1f4a5c0b41439f`。
- 完整被审候选：`b0d8d83750c48cd951c16b50cfa28a7898976e72`；R1 技术 PASS，P0/P1/P2 均 0；[审查交接](../coordination/handoffs/P02-review-r1.md)提交 `8e4fdbd7374130c77262a57e55049f9cef4bf651`，父提交正是完整候选，只新增 6 个允许的审查文件。
- S0 非强制整合为 `bcc896e0912dde474f463f0407becbde2989c876`，保留 R1 原始 SHA；后续仅更新项目文档。实际 main 的 src、tests、data/manifests、公共配置、依赖锁、冻结清单、检查脚本、CI 和 LICENSE 均与被审候选字节相同。
- [最终 CI 34006711558](https://github.com/kris0516/ToolAlign/actions/runs/34006711558)的 Python 3.11/3.14 两个 job 所有步骤成功，job ID 为 101415140676 / 101415140628。CI 默认测试范围不等同于下面的 338 项真实 tokenizer/独立反例组合。

S0 另核对 R1 的 26 份命令日志及索引、4 份私有结果、3 份原创探针摘要，与已提交证据完全对应。R1 完整数据审计、浏览器观察、历史失败与未测项保留原文；没有通过修改被审生产代码来关闭问题。

## 实际 main 检查

运行区间为 2026-09-06 02:44:03–02:44:14 UTC，本机 Python 3.14.7，纯 CPU。真实 tokenizer 环境的 27 个 distributions 与固定清单逐项一致；使用已核对的只读 tokenizer 文件，不加载模型。原始 argv、环境、时间、退出码和输出在 S0 私有证据目录保留，未覆盖旧包或其他 worker 的证据。

| 实际检查 | 退出码与范围 | 原始日志 SHA-256 |
|---|---|---|
| `uv sync --locked --python 3.14` | 0 | `b4e9d5f92950c6ebef8191e443e236bef05db17b9cc9d492afd6bae2ff055853` |
| 完整 CPU 组合 | 0；**338 passed，0 skipped** | `08aff89005ccb5478d6a42406a8b232e42558285b1bcc0a1d377ffcc1c2ab994` |
| `uv run --locked ruff check .` | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `scripts/check_contract_freeze.py` | 0；4 个冻结文件 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `scripts/check_public_content.py` | 0；173 个追踪路径 | `a1b028a00bc5b0948702a13c571a0891f2b2e9b47dce209eda98bb9c6c427603` |
| `scripts/check_source_distribution.py` | 0；241 私有探针 / 18 公开对照，三种构建路线 | `76dece769f663851320b3777bea643bd994bce792763e6e87de371cb9ff7ebfe` |
| 正常 `uv build --out-dir <私有制品目录>` | 0；sdist 和 wheel | `8829908f7d28c74a18cfc73f3bfe00bc5dba4b30fce2e053945f1fa274a6d85f` |
| `uv build --wheel --out-dir <私有重建目录> <实际sdist>` | 0 | `5c963ab81a0136628deaa751aa2a32f4c25c5b87ed61b5959069b06f8d580309` |
| 隔离 rebuilt-wheel 验证 | 0；14 条子命令全部退出 0 | `17e22775cb27716ba746e038fb4556c3daddad515300778c454ae094a743b212` |

338 = 仓库 180 项（含 17 项真实 tokenizer）+ P00 独立 46 项 + P00-r2 独立 72 项 + P02 独立 40 项。不重复累加默认环境的 skip 或历史 shared01 结构快照。核心实际命令如下，`P02_CPU_PYTHON` 与 `TOOLALIGN_TOKENIZER_DIR` 的本机值在私有映射记录：

```bash
PYTHONPATH=src TOOLALIGN_TOKENIZER_DIR="$TOOLALIGN_TOKENIZER_DIR" "$P02_CPU_PYTHON" -m pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py reports/review/P02/test_p02_boundaries.py
```

## 实际包与安装行为

| 产物 | Bytes / 文件数 | 内容核对 | SHA-256 |
|---|---|---|---|
| sdist | 135363 / 60 | 59 个追踪文件逐字节一致 + 生成 PKG-INFO | `36233176f3ddc1e5c70ef1d307bbfdace412cbf6d07f87ff30cc22934efd6f5a` |
| direct wheel | 51292 / 29 | 24 个源码/资源逐字节一致 + 5 个固定 metadata 文件 | `bfe806be8e46617896ccae4ffab523c1132204d3150e5f6380e854f2e237f558` |
| rebuilt wheel | 51292 / 29 | 从上述实际 sdist 重建，与 direct wheel 完全相同 | `bfe806be8e46617896ccae4ffab523c1132204d3150e5f6380e854f2e237f558` |

三份真实归档的未追踪载荷、缺失预期成员、源码字节差异均为 0；拒绝重复、符号链接与逃逸成员。与 D1/R1 早先的安全包比较，成员集合相同；sdist 仅 README.md/PKG-INFO 改变，wheel 仅 METADATA/RECORD 改变，均源于本次 README 更新。旧包先核对固定大小和已知 SHA 后才比较，没有读取先前失败的私有内容归档。

隔离环境通过锁文件导出默认运行依赖，要求依赖 hash，随后以 `--no-deps` 安装 rebuilt wheel；清除 PYTHONPATH/PYTHONHOME，并以 `python -I` 从源码目录之外执行。

- 安装后的契约摘要及五类 fixture 验证通过。
- 14 个包/数据模块的真实导入路径均位于独立 venv，MLX/Torch/Transformers 不可导入且未加载。
- 数据 CLI help 正常；安装后的 `compare` 重新核对原两份冻结构建的 18 项制品，返回 manifest `87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`。
- 使用显式提供的、字节已批准的公共 policy 文件和原创小 fixture，安装后的 SourcePolicy、字面调用解析和单决策转换通过；typed default 保留为 annotation，没有补入实际参数。该检查不声称 wheel 自带用户数据或所有运行配置。

机器摘要 SHA-256：`87b6de029f2c22eae402b2fcf615e0af62f7c97625367c5c48bc800ad5ed3559`；归档 inventory：`d773d3db4df314545f39f11123761e793cfc131f4d967b29df421ff73a2839d2`；隔离摘要：`227bb39b19922393369069bf2b620682c96653669dd858f4ca267cba32f6c577`。私有验证驱动的 SHA-256 为 `f7d60ed8548cb7c40d5c99e7d46f8d2ad3ee8de511c85ad5dca8246eb3d17d1b` / `a2df7ba50b5329a6937b35ad5448d1ac77399e8e76c85aa8cf5e0c3c702de064`。路径与原始日志留本机，公开扫描仍只是有限检查。

## 保留的门槛

P02 数据代码已 MERGED，**数据语义与整包不标 VERIFIED**。kris 的实际人工审阅已请求但尚未收到结果；R1 的技术核对、浏览器观察与机器统计不替代本人审阅。冻结的 100 来源/114 决策材料保持，填写位置为单独副本。

训练配置仍须绑定 manifest 和序列化口径，明确处理 113 条超过 2048 的样本；8192 的数据探索上限不授予训练窗口。P05 的偏好对数值阈值未套用 P02。P01/P03 未验收，P04–P09 未因本次技术集成而获准跳过依赖。未运行正式训练、偏好生成、BFCL/隐藏最终评测或推理服务，未上传模型/数据，也未产生付费资源。
