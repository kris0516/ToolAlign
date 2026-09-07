# P02质量修订：S0隔离集成证据

CPU技术集成通过，PR12最终CI与main验证待完成。S0从 `769f9ffc7faf0025900da0035d6309fc975e338f` 普通合并原R1 review `1e45cf2c2ea07b703be548a112ef16e1ef134ee9`，得到 `f90be6042b95b8af0095107ff2f2528379fac1ff`；原候选 `9b7cf019b1d55501a7e656dbfb79b13bc7369fa0` 和审查SHA均保留。

478个实际文件严格等于main文件、12个候选新增文件和10个R1新增文件的并集。S0全部执行前后的提交、工作文件hash及干净状态一致。原R1交接已通过[14,011路径核验](S0_P02_QUALITY_REVIEW_ACCEPTANCE.md)，本轮另验证3,355个文件路径，证明SHA-256为 `ffa0a15436d6b2b7254130f6071fa464b2b8f9a73fede798e7185b319e33b5d9`，封存检查发生于04:11:04–04:11:05 UTC。

| 实际检查 | 结果 |
|---|---|
| 主CPU回归 | 1,007 passed / 2 HF-only skipped；04:06:12–04:07:09 UTC |
| 格式、截止时间、训练绑定、SFT CPU、native CPU、质量边界六组 | 60 + 2 + 13 + 44 + 34 + 26 passed |
| 总计 | **1,186 passed / 2 skipped**；110 subtests单列 |
| Ruff、显式Python文件、冻结契约、公开扫描、diff | 全部通过；公开扫描478路径，四契约保持 |
| 本轮新sdist/default wheel/由sdist重建wheel | 三份实际构建与全部成员核验通过；127个sdist源码、60个wheel包载荷 |
| 新默认安装 | 离线无依赖安装，三项正向入口通过；八项实际输入替换以exit 1 / input_hash_mismatch拒绝 |

共27条实际命令均符合预期退出码，包含八条预期拒绝；原始参数、UTC、stdout/stderr、子进程回收和源码绑定保存在本机。18份实际runtime证明分别覆盖七组CPU与十一项安装命令。安装入口使用`-B -I -S`与非源码工作目录，全部60包文件及实际导入来源对应新target；八种optional依赖不可见，未导入分词或模型框架。

新sdist SHA-256 `65623012f5046bbc46160c99d384d94532e8d30a5a08e684ca67652d5177b629`；default/rebuilt wheel均为 `7de39c233e46a1bda302e77361ce55ef5a0c5a6f42265d5a5a50ce2dd2e2e95b`。归档检查证明为 `99fc0704e8f4d61f07b485a994362eb8a41dd2bfbfb9224bd8d9f4e3e6a59030`。复用R1归档检查器自身不构建包，其`new_archive_builds=0`仅描述检查器动作；本次S0两条构建命令在04:06:59和04:07:42实际产生三份新归档，不能据检查器字段把真实构建记成0。

安装版verify消费已封存修订视图，确认32来源/40决策暂挂及原选择过滤；compare读取既有两引擎16例记录，完整records hash保持 `0908dbf24fe43acb89ccb063427b2f5fa2f4803baace5ec1d57aafc2907bf6dc`。本轮未重建全量修订视图、未新增16例材料编码或框架运行。两条直接重标及一个后继仍在staging，未进入有效训练。

S0汇总检查器首次错误读取compare输出不存在的`new_token_encoding`字段而以KeyError退出，原脚本/命令/日志保留；按实际schema和已核验隔离runtime修正后通过，未改变候选、测试、归档或安装执行。另有两次只读辅助查找/私有映射结构错误，均未改变生产或旧证据。这些不增加正式质量修订计数。原D1/R1失败保持。

封存时新私有制品2,426个、157,079,321 bytes，低于2GiB；该时点统计不包含尚未写完的本次证明与发布后材料。没有新环境、下载、付费调用、GPU/模型/框架运行、浏览器或公开数据上传。

R1已于04:03:33 UTC按完整授权 `769f9ffc7faf0025900da0035d6309fc975e338f` 原生接续精确E1 `5270d1e` 的CPU审计技术复核，ACTIVE，intake尚待交付；旧450份公开字节已由原Git与独立副本保留。Q1固定50来源/60决策独立裁定继续。G-DATA和正式P04未通过，`training_authorized=false`。
