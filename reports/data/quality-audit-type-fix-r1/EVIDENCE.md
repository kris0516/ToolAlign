# 类型修订证据索引

全部原始记录、已有材料的反例副本、新视图及精确路径只存本轮私有目录。公开文件包含代码、原创夹具、聚合数字和 hash；没有来源原文或判断表。命令记录包含真实 argv、开始/结束 UTC、退出码、执行时 HEAD、工作区状态、使用的 Python 源码逐字快照及日志 hash。

## 关键封存与来源

| 对象 | SHA-256 |
|---|---|
| 原 S0 类型发现证明 | `80e0f558042bd92cdaaeb73e63f7f322d733b80de289d57d293956a844ea540e` |
| 原 R1 10 项夹具正文 | `395a8797147834915230078299ff6f6f8ded0c21780c52c3eb7cec43efbfca8a` |
| 原 R1 3 failed / 7 passed 日志 | `bfdf791ab09cf510d666129c5d2d705b8e3de26c13e523d05e91d05292f73adc` |
| 同轮材料发现证明 | `07d136fda015d93a1ddcb84f87748695469794171330a952d008512e5d17b34a` |
| 原有效材料反例脚本 | `8da59f13360ccb8162f49c85cf64c992479068a0c04274ae826f53e810549b4f` |
| 新合并 intake | `766bc3fc5425d4bd5738f07d6660132726fb7b72b0c90817f22f4bc5470319d0` |
| 17 份原材料证据副本 intake | `d2d532f0997b98ae3ed88f016c57fe63ea7cd15ca64eba22a274be56657a583b` |
| 43 视图新旧影响映射 | `3073ebd319330b0f8ee0c09b149133c4d51624c693628a141470db4af1316f02` |
| 材料反例 / 数组检查 | `5e100d6832da4a6262231e5a4a66a21bcb461d106b7b25410e272b77b78ff5b7` |
| 16 材料新静态检查 | `78e2d3094b432425ec927129303ecf4bb260d32017749891a5b9b215fcf827e2` |
| 保全核验 | `178e18289278ef5f3afa4ea287cec9f92ef0f710c0bfdc09398bab1388fe4f5a` |

原 E1 完整 seal `adcf1a3ffd22a3803afc4cce7914f3bb37ee515a2eee282733521b05ff349889` 和 receipt `b4b9d5898594d2c9fc9026ea75a197c4b82ee67b78a6afaa745fbb93fcc9306c` 保持。新完整候选及 seal 在最终交付回执中单列，避免把封存文件自身 hash 写入自身。

原 R1 夹具为 12,865 bytes。公开执行副本为 12,967 bytes，hash `130b9332a9e71e0c9b7fec1fe6b1987f547c1f61ae697beb42478233cc11f042`；去掉开头两行注释后与原字节相同。私有原件保持只读。R1 材料探针中的私有输出路径未直接执行；`check_material_type_fixtures.py` 使用其已封存 record / 原页 / 改页，输出到新的目录。

四个修复模块的实际测量字节对应源码提交 `74a8d348e75fc57535ee0b75806106486d8629ee`，后续仅公开 R1 副本增加注释和交付文档。视图及材料自查没有重跑或换用后来提交的时间：

| 修复模块 | SHA-256 |
|---|---|
| semantic_view.py | `3d0b6c7cd83dc5e0dabe59414a1a644f4cc233df2e6465ce0595f70fd07c9d5a` |
| verify_semantic_views.py | `992f570f79fbb9c795bab16acaf7068d0d18a7f3b7ad375e2f0ba4c12749ce51` |
| check_materials.py | `0387af730e389cea56587d4d03be21edcc4a0284938017e0a411de5deb3f11e2` |
| json_values.py | `fe9ffb1be5a824f42af4cf7ac302e2aa3648674ac8d774f7eecb011612d3550c` |

## 复现入口

以下私有路径变量须使用 S0 精确授权的封存输入，输出须是新的私有路径；不是许可再次消耗本轮已用完的真实输入预算。固定视图脚本用排他方式创建输出目录并保存开始标记，不能删除后伪装成首次运行。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -B -m pytest -q -p no:cacheprovider --basetemp="$TYPE_FIX_TEST_OUTPUT" reports/data/quality-audit-r1/test_sampling.py reports/data/quality-audit-type-fix-r1/r1_test_independent_boundaries.py reports/data/quality-audit-type-fix-r1/test_json_types.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B reports/data/quality-audit-type-fix-r1/check_material_type_fixtures.py --fixture "$SEALED_R1_COUNTEREXAMPLE" --descriptor src/toolalign/model_io/descriptor.v1.json --output "$NEW_MATERIAL_FIXTURE_RESULT"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B reports/data/quality-audit-type-fix-r1/rebuild_view_impact.py --audit-root "$ORIGINAL_AUDIT_ROOT" --output "$NEW_VIEW_RECONSTRUCTION"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B reports/data/quality-audit-r1/check_materials.py --inputs "$ORIGINAL_16_MATERIAL_INPUTS" --descriptor src/toolalign/model_io/descriptor.v1.json --output "$NEW_STATIC_RESULT"
.venv/bin/ruff check --no-cache .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B scripts/check_contract_freeze.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B scripts/check_public_content.py
git diff --check
```

最终 39 pytest 的原日志 hash 为 `0920fa3e8fffd6a917aee56d29e9da73a41a9ba71faa6b5a6de7fe26f4f6cea2`；固定视图执行日志为 `a9369bba519a60cf236cd1b8268628ee6fda035c629e6d2f44c2be23b39bcf34`；固定材料执行日志为 `6923c6290b4a51eb405d216c82a7ffadcca36bd555a5adfd9a37dfff29ce6711`。三者执行时间、实际 HEAD 与逐文件来源分别保留，不把摘要相同当作新的实验。

保留的本轮失败日志：合并原代码反例 `f7a5af3a9e7928f4f13e9e54a375ff1d507926114d1481b6008830707075372b`，新夹具 schema 错误 `8f160a0bde0fb8ae43df99f163a18b9f22a962b6d69e22bbaf326fa3eda991b6`，Ruff 参数错误 `9f028e2ca243a14fe2d620d7594cf1848802af1796322616fec39fa2865a8532`。只读副本写入工具错误另有辅助事件记录。额度中断和这些辅助错误不增加正式审查失败次数。
