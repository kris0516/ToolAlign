# P04-SFT-DATA-V3-FD-CLOSE-FIX｜构造失败时释放输入 FD

状态：IN_PROGRESS，T1。已于2026-09-07 23:03:59 UTC按完整 `df37a3c64bb114b70ab8221d167ea021e22524e7` 原生派发并核验新轮ACTIVE，gpt-6-astra/max；656路径/12授权/7输入派发前核验通过，证明 `ebef278ddbb0a2a0f09c9a0b7cc0b2e057c69844b8658cc19114880d46d7735f`。新branch/intake待交付。code_base/父候选 `1769046468eb2ebfdd9e982ba4938833760e3fe0`，tree `1373bd4c838a1af395a1ede4f7c4d7029ffad271`；这是待修订的候选，不是已验收生产基线。完整 authorization_commit 由 S0 原生派发提供。统一 gpt-6-astra/max；沿用原 T1 独立 App 任务及隔离 worktree，新分支 `codex/p04-sft-data-v3-fd-close-fix-r1`，新私有 scope `p04-sft-data-v3-fd-close-fix-r1`，禁止 sub-agent。

目标只关闭 [S0 核验的 P2/F2](../../reports/S0_P04_DATA_V3_R2_INTAKE_AND_FD_FINDING.md)：预检查后路径变为目录，成功 `os.open` 得到的 FD 在 `os.fdopen` 构造失败时仍打开。把裸 FD 到 stream 的所有权交接和构造失败清理写清楚，异常时释放同一自有 FD，保留原异常/原因；正常读取、hash-only、大小/预算/摘要、同 FD 核对、O_NOFOLLOW/O_NONBLOCK 和原 DataError 分类保持。正常成功交接后的清理由 stream 完成，不能再次关闭已转交或不属于自己的 FD。不要复制修改其它 I/O 组件或借机重构。

仅允许修改 `src/toolalign/training/sft/data_v3.py`、`tests/training/test_sft_data_v3.py` 的相关部分，新增 `reports/experiments/P04_SFT_DATA_V3_FD_CLOSE_FIX.md/.json` 和 `coordination/handoffs/P04-sft-data-v3-fd-close-fix-r1.md`。固定配置 `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1` 不变。禁止修改旧报告/交接、其它生产/测试、数据、模型包、CLI、依赖/构建/CI、S0 协调和其它 worktree。

先保存完整授权中的 AGENTS、GOAL、PROTOCOL、REVIEW_POLICY、REVIEW_FAILURES、RESOURCE_LOCK、本任务、原非普通文件修订任务、数据 CPU 任务/配置、S0 原修订接收与本次发现报告。核验旧分支干净 1769046、621 原公开 Git/快照、最新原 seal/终态回执、原输入/失败及 root identity；保留全部旧分支/私有封存，通过既有只读引用绑定，不重新复制历史大目录。新身份只写新 scope。R1 对 1769046 的完整正式审查继续，届时由 S0 补充原 review SHA，在同一修订范围接入；不能提前自签或调整失败 counter。

新最小输入 manifest `6ad59fc55d8395ced97541ff53590a0fec2c8a744b7cbd48c6c829fd62bbcfa5` 及七份副本由 S0 私有分发。原六项测试 SHA `24d475c6f762b00bd218d609a81a4e019e7996a6eee946f671431c3916eb7a13` 和原 5 PASS/1 FAIL 保持，不重跑旧失败来增加次数。读取最小无包装观察的原结果即可，不执行会写入输入目录的原观察脚本。

修订后用少量原创 fixture 验证真实目录替换异常及时拒绝且 FD 已关闭、其它构造失败的清理/原异常、成功读取的所有权转交和错误后同 FD 清理。只运行本模块原 147 项及必要新回归；原未修改六项独立测试在新源码和新默认安装 target 各最多一次，使用互不覆盖的新输出根，所有原反例/失败保持。若失败，保留并交具体原因，不覆盖输出或无说明追加。原固定 f44 FIFO 实物探针不再重复调用；稳定 FIFO/替换 FIFO 由既有相关单元和原六项测试验证。

可在既有离线构建支持下生成一组最终 sdist/direct wheel/sdist rebuilt wheel、一次新默认 target 安装。核对实际成员、metadata/entry points/LICENSE/RECORD 和源码时点；外部 cwd 验证纯导入、来源和六项原创 I/O 检查。无需创建环境、安装依赖、下载或运行全历史测试。每次 pytest 使用本任务独占的新 basetemp；公开输出测试目录没有 `.toolalign-local` 祖先。FIFO/链接只按 lstat/readlink 单列，不能纳入常规文件 hash 流。

真实 609 输入 prepare/verify、13 例转换/导出/回读额度均 0；沿用原固定消费记录的实际 1769046 时点，不宣称新源码已消费真实数据。全数据构建、新编码、框架/模型/GPU、优化/生成、业务 API、浏览器、模型/数据上传和新费用均 0。新增制品不超过 1GiB。保留实际 argv/UTC/exit、完整 stdout/stderr、源码和安装来源时点、自有进程回收、全部失败及最终 seal。

先回报真实新分支/身份/输入及旧证据 intake；交付精确 candidate/tree/parents、差异范围、测试/原反例、归档/安装与最终封存后普通推送并结束。不给自己的修订签独立 PASS，不合并 main。S0 在完整交接后安排精确 R1 复审；复审真实数据消费额度另按必要性冻结，不默认重跑。普通回报 S0 省略 model/thinking。

原正式R1已同范围接入：`58212d26bdb1c6a681a1ac34ccae854daefca8d3` / 唯一parent1769046，FAIL仅F2/P2；原F1分项关闭。T1于23:18:36 UTC交付三份原Git补充副本，S0完整原review接收于23:19:19 UTC通过，证明 `b5332709432e9361bc7339ab870398c64c6a623a0164bf505f54ddf4bebad92a`。原df37a3c修订范围/额度/同轮保持；9e08a096及157/原六项两路线通过仍为T1中间自测，完整候选与新独立复审待完成。
