# S0：质量修订与委托AI复核的中间证据

2026-09-07。状态：中间制品/审阅交接核验通过，D1完整候选与E1最终审计尚未交付，R1未签本包。原main技术验收、原委托AI记录和失败保持；training_authorized=false。

## 数据视图与选择

S0于01:57 UTC独立核对D1数据模块`53bf6bd617a454c022fdd03c09276b162df1f1fa`对应的两份实际生成目录。24份稳定输出逐字相同；原32来源的40条有效决策完整暂挂，其他原Example的JSONL字节、身份、group/split及选择相对顺序保持。暂挂来源所在group中仍保留5586条其他来源Example，没有删整组。

| 集合 | 原条数 | 当前有效 | 暂挂 |
|---|---:|---:|---:|
| train | 7515 | 7475 | 40 |
| validation | 234 | 234 | 0 |
| smoke/train | 1600 | 1593 | 7 |
| formal/train | 6013 | 5980 | 33 |
| smoke/validation | 197 | 197 | 0 |
| formal/validation | 217 | 217 | 0 |

两条直接重标及一个后继前缀按原草稿独立重建，新规范化ID/parent绑定相符；它们未进入有效数据或选择，继承观察仍未验证。S0核对949条当前文件/源码快照路径、四份原命令，证明`5bd602de8be0c36135c4b6d17f2f64f0275ab5c96eaa51411531074111b1ac07`。首次生成因CSV上下文包裹的notes与原提案不完全相等而FAIL，原记录保持；两个文件仍分别精确固定，修订绑定检查后生成成功。成功A执行时HEAD为86b80ba且新源码未提交，B执行时HEAD为53bf6bd；两次源码快照均44dcfdbb且消费字节相同，实际创建时间为01:46与01:48，不改写为同一次运行。57项单元检查为D1当时自测，完整回归/打包仍待最终交付。

## 修订后16例材料

材料模块`1c90ce0ba5f505e4ca4e7118012c351c5e9dff2e`已实际用两个原有CPU tokenizer引擎生成同16例：10有效train、3原创协议、2直接重标、1后继前缀。S0于02:03 UTC核对99条当前文件/消费源码路径及两份原命令，完整记录逐值相同，逐例原来源/新选择/parent身份、Action文本、全数组mask/next-token shift/EOS/padding相符。两CSV身份不变且判定列全空。证明`20dfcf0d4d0d39c44883b1a501626b8f42f54ea195e52fbcc137edff0f01a2a6`；reference manifest `11469fdf48ff5c8caf5882b5e02f1c66d8a410303320dfbfc4dd57b8e6c65d57`，native manifest `112f63a488672502697996dcc265fadfe1a3a388b9d8d78f2ff28caddc6733be`。

S0没有新增tokenizer/模型/框架运行；两个worker测量合计32条引擎记录，独立例数16。静态文件存在不代表实际浏览器显示，后者继续NOT_RUN。本批已于02:14 UTC按完整eca077730648b91c03781306270356ddd70662ac及[精确追加范围](../coordination/tasks/P02_QUALITY_MATERIAL_REVIEW.md)原生交E1独立填写语义与token/mask两列，显式gpt-6-astra/max；原轮ACTIVE已核验，追加输入intake待确认，原180来源抽样保持。

## 原32来源的独立初判交接

E1已先独立判定原32来源/40决策并封存，随后再对照原报告及两条草稿。S0于02:09 UTC核对87个当前文件的hash、逐目标与原packet/turn/Action身份、审阅者与UTC、原判定和等级迁移；原初判seal的记录时间早于比较/草稿报告。证明`9bd9290d2cb3165ed0b17ce430ea4481c8de7bffe6efe24d51c4527c48a6e3c9`。

E1来源级判断为12 fail / 17 unknown / 3 pass；决策级为12 fail / 18 unknown / 10 pass。与原报告比较，21来源同级，8个fail改为unknown、3个unknown建议pass。主要分歧是缺少ID/日期约定应记依据不足，以及候选检索这一下一步动作是否已合理；两条直接草稿的修改获语义建议pass，但旧观察和后继条件未因此获通过。此处只接收E1判断，不把它们写成S0已裁定或真实API验证。当前32来源暂挂保持，三条建议释放未应用；原判断原件未改。

E1继续冻结的180新来源/200决策审计，随机、定向、旧32和追加材料的分母分开。全部新发现先封存交S0，再形成精确整改授权；不实时改动D1输入，不按关键词自动判错，不外推全库质量。完整修订、独立R1、最终CI/main和G-DATA仍待完成，正式训练未放行。
