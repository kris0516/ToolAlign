# P02-base-r2｜公共基线同步后的待审候选

D1 / work/p02-data / gpt-6-astra、max。本轮仅CPU基线同步与证据确认。**当前适用检查通过，数据实现和人审输入完全未变；P02/G-DATA尚待独立R1及kris。**

## 提交关系与变更范围

- S0生产code_base：`37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`。
- 同步authorization_commit：`f2a271be616cdb53c01e8d671029f31ae140c037`。
- 同步前完整P02候选：`46f546504f73588caa2e71aac316c3c312306df6`，原生产实现 `9be07a5b88d1dac1a6e1fea30358af1049b1119a`。
- 本次非强制merge及精确受测生产提交：**`9bbd7d732cb9f84be2f1ca065beed9c9178801bc`**，父提交为46f5465和f2a271be，无冲突。
- 最终完整候选为本交接所在的后续证据提交，完整SHA随原生消息交S0；该提交仅新增本交接与reports/data/P02_BASE_R2.md/.json，生产/包输入不变。

已按授权读取并私有保存AGENTS/GOAL/PROTOCOL/任务包/main验证报告的精确提交版本。Worker没有手改公共配置/依赖/看板，公共变化全部来自已授权merge。原P02-r1、旧57项S0-SHARED-01结构快照、旧数据构建与原候选保持，未改成当前绿色。

## 实际测试与制品

当前完整适用CPU **298 passed，无skip**：180仓库tests（含17真实tokenizer）+46 P00首轮+72 P00-r2。日志SHA `900f507dcbea077dd1fef513ff350e8c1609476d943e05758992f23cd1f96ef8`，退出0。默认核心另为163PASS/17明确skip，日志 `5d7b3b55b0a7ff1d0b3e8c552e5af1f2b6d51e847e1b6a93ad30901bf8a8a556`，退出0。旧“唯一extra”等57项为历史结构快照，不适用于新增合法组；旧文件hash `8a5b176def3d660a049d23a12c824418e999bc8da4da0fa8b249eea46f86f9f0` 未变，未运行或计入本次298。

合入修复后正常 `uv build` 的sdist和wheel均成功，退出0，日志 `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75`。实际归档：

| 制品 | Bytes / 文件数 | SHA-256 |
|---|---|---|
| sdist | 135,139 / 60 | `d7ee2db8d9ce257db9a035adbee389316f4a89d91832494117336e859c84a241` |
| wheel | 51,140 / 29 | `78ad37239a3d1023295d2e7a73be19583bcd335a8f50b47ca1cefb61f86b4672` |

sdist除PKG-INFO外、wheel的24个源码/资源，均逐项对应Git追踪字节，未追踪载荷0、私有路径0；11个data模块均匹配原构建manifest。核对退出0，日志 `2e52810f7553bd2b664df67d853f365acbcd9e70f27d974ba82e28ebe4ad5885`。原失败sdist继续私有保留，未解包、上传或删除。

当前归档回归241私有canary/18公开对照、R1-r3追加45私有/21公开对照均在sdist、重建wheel、直接wheel三路通过；不相加成覆盖率。日志分别 `ed29958888158ebbdb90bbb15eac534d34468e439fe55497e0f7e941d5c875ab`、`b84e255ba28081a6556b77f2fee85652c734f564ced6e06cbf615ab87161a37b`，退出0。

原P00隔离安装脚本在临时Python3.14.7环境实际验证默认hash依赖闭包、安装新wheel、schema、五类CLI fixture、脱离源码导入和无ML后端，通过；日志 `f116a443c64367b8688e49c72243b21917169f1af8c7e208d2acb85d4d9b8047`，退出0。默认环境12个distributions，无Torch/MLX；锁中93条不是已装93包。

ruff和冻结契约退出0，日志分别 `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`、`cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190`。完整命令/UTC/耗时/log hash见 [本轮机器证据](../../reports/data/P02_BASE_R2.json)，详细说明见 [本轮报告](../../reports/data/P02_BASE_R2.md)。公开扫描结果在证据暂存后追加。

## 数据与人审材料保持

src/toolalign/data、tests/data、data/manifests及旧P02-r1均与46f5465完全相同。合并前后分别重读policy-a/b的18项产物与manifest，所有hash保持。本轮没有重新运行数据build。

- 共同canonical build manifest：`87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`；根manifest文件SHA `c728dfe385e340fadf1e5949976c012709fc10a1dbca9010548edf74785259e5`。
- 当前有效包仍为 `.toolalign-local/policy-a/human-review/`；100来源/114有效决策，原34分层保持。HTML SHA `6193aa5da4a5dd4a5293472dd424ed1839e954d79d8d79afe524cd830b1dea8a`；samples SHA `d8a608ba59fa375762aca65412f76fbef29046897b9e546c359bdccc3de62033`；人审manifest SHA `cf82d8f9a5848c3cae0069d27a7549f385aabfdc4586a5de343795795883162c`。
- kris填写副本仍是 `.toolalign-local/p02-human-review-submission/review.csv`，当前文件SHA `eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`，与冻结空表相同。source_index/source_record_hash/example_ids/strata身份字段hash `b7878f5ced14bdaa69f4cbbbffef177e2912625a411858e348cfef6b9b91590c`，前后相同。
- reviewer/verdict仍全空；未填写kris结果、改采样或改数据。浏览器渲染NOT_VERIFIED保持，由S0接手本地展示。旧零strict包不是本次人审入口。

保留S0给出的P01窗口2048与113个长样本限制：原有效数据8,228例中8,115≤2048、113在2049–4096；数据build max_tokens仍8192。本轮没有为P04截断、筛选或重新分组，也不授权P04训练。

## 后续与限制

本轮所有实际检查退出0，无新失败。数据/环境/证据磁盘测得1,191,376KiB（约1.136GiB），低于5GiB。未加载模型、使用GPU、修改其他worker、运行训练/评测/服务或上传制品。

请求S0将本轮完整候选交R1复核，并继续安排kris在原有效包完成真实语义审阅。共享支持通过不等于P02验收；P02 main集成、人工门、模型实验及P04长样本处理均NOT_RUN。交付后停止执行，等待R1/S0反馈。

最终证据暂存后的公开扫描退出0，日志SHA-256 `3fa20bfcc1706e4230b9c04ee7b2a80a19ea30f0015c5406775ea4c8da5af449`。原始输出：PASS: 167 paths scanned in index and working tree; heuristic check, not a privacy guarantee。
