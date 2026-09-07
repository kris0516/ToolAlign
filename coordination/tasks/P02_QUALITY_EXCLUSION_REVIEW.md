# P02-QUALITY-EXCLUSION-R1｜v3定点排除与复用材料技术审查

状态：READY，待原生派发。精确candidate `5825d789ee89afedbfff31e828223608c6f435e2`，实现/实际新编码 `6054b349c344cbbad30c12ce8fe8820c59e8bc10`，完整D1已交付/原生空闲；S0核验32,579路径/644链接、44原命令/18源码epoch、完整数组与实际归档，见[完整接收](../../reports/S0_P02_QUALITY_V3_HANDOFF.md)。本轮S0 authorization_commit以原生分发的完整SHA为准。代码基线为已验证`d3e56f68ebd67cc576d912b6f06636682b4170ab`，R1从上述完整candidate创建新分支。

R1使用原有独立App任务，gpt-6-astra/max。新branch拟为`codex/review-p02-quality-exclusion-r1`，从精确candidate创建；新私有scope `review-p02-quality-exclusion-r1`。先按届时完整授权保存AGENTS/GOAL/PROTOCOL、REVIEW_POLICY/REVIEW_FAILURES、本任务、D1 v3任务/精确配置、ADR-0025、S0完整交接和Q1新来源接收报告。切换前核验原R1分支/提交、旧公开Git/快照、私有封存及根identity，具体hash在正式分发时绑定；新身份不覆盖旧identity。

旧R1精确提交 `d5b8d17207be7295f3ae5c6a51edd9b8fe968001` 已原生completed/notLoaded；S0提前核验498旧公共文件、2093本轮旧scope文件和769历史链接，preservation SHA `74d655d5176ba7563eeb3264a806e6b97310ea36cc41b42252712d968221fd91`。完整交接manifest、原S0输入与实际数据/材料/归档的只读路径在私有分发中给出。不能覆盖旧pytest basetemp；本轮每次检查使用新临时目录并计入1GiB。

本次实际绑定：D1 completion `1d65726003a5eed3b6b74a4ba77bc0e49cd724d0f0dab82733ac8ec9e3e7cc0f`，收尾receipt `871c318fe264ec84c90a37aeb20b92f07ce71e6992c4ba4b71bd2fea2e04920d`，S0接收证明 `2eba41c079a18a4e973738c5caf3ca3309bb211a1e5f1f2f80be90620615e379`；输出manifest `f4569b8b16a6c42bd500cc7c977561b770435954e42ced177e36e857b9776437`、quality revision `919ee616fd11993f39bbab6d38146ea827f4bbc3d7bafc07aae0e2c7dd95e5c8`、13例records `a41f5c24a55eb5e4fed434b9352b655fbf78e5aa68276de5de183671c81412de`。D1的2/2全量输出与4/4新sequence额度均已用尽；R1自己的下述独立CPU额度另记，不能重启D1编码预算。

完整审查新增v3 wrapper、材料模块、S0精确配置与新测试，不只看末次提交。旧生产/测试/依赖/配置保持字节身份。固定v3输入manifest `ebbaf56bbb5730b5d31eca195d5ac7772d148ff876fc96be1c1c5dbbadf51e06`、配置 `784aa699026ebb149d720745f461a9cfd493036cd0bf09a72702a81e2db45261`；不擅自用当前台账或其他任务输出替换已冻结输入。

独立核验P02-Q-081整来源的两条决策均排除，包括错误历史之前的目标；原两个Action的PASS及历史子发现不改。旧83来源处置、3项原字节恢复、同group其他来源、staging非晋升保持。预期有效train/validation为7419/230，formal5938/213，smoke1583/194，实际交接后绑定真实数值。原选择不补选、不重排；`parent_selection_rank`继续表示v1，`previous_selection_rank`表示v2，本轮rank连续；Example原行、group/split和lineage保持。

材料核验固定13个唯一身份：11个旧例按Example身份复用，2个新例按S0固定名单编码。两engine的完整sequence、padding和token_texts逐类型绑定；case编号、rank、revision和HTML更新有明确映射。旧11例保留原运行时间、源码/命令与原封存，新发布不得冒充重新编码；两新例必须绑定S0基于Q1正式裁定发出的精确放行、真实原命令和源码epoch。第三个仅来源审核的目标不增加编码。完整材料保留空白判定，实际浏览器观察和真实trainer消费不得从静态数组推断。

独立原创小反例重点覆盖整来源局部遗漏、旧/新rank混用、错Example复用、旧revision或错误parent run冒充新绑定，以及数组数值类型、原时间/源码身份、配置/hash、final split越界和失败发布。检查新路径复用已验收纯函数而非改旧常量、全局patch或复制完整生产器。D1的定点自测不替代R1反例；不机械重复与此次修改无关的427项历史HF/训练组或为了凑分母启用额外tokenizer。

仅现有纯CPU环境。最多一次全量v3独立构建、一次完整13例静态材料核验；现存三归档直接核对候选载荷/RECORD/metadata，并允许一次临时target安装验证新入口。真实分词0、新归档构建0、新持久环境/依赖/下载0；无需为同字节归档重建。新增制品≤1GiB，独立原创小fixture不计全量构建。无模型/框架/GPU、API、浏览器重试、训练或生成；最终集只作hash/隔离元数据检查。

允许新增`reports/review/P02-quality-exclusion-r1/`和`coordination/handoffs/P02-quality-exclusion-review-r1.md`，不修被审实现或修改S0台账/看板。保存实际argv/UTC/源码时点、退出码、stdout/stderr、失败与最终seal，给出精确candidate的PASS/FAIL/BLOCKED及P0/P1/P2。普通推送并原生交接后结束；Q1另验实际处置/材料，R1技术结论不自动放行G-DATA/P04。同问题五次规则按S0稳定台账执行。
