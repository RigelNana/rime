# 蓝三字词表与词频

`lansan_guanfang.dict.yaml` 保留蓝三官方字词和编码，`ls_ci.dict.yaml` 保留此前合并使用的词表。合并后的公共词库为根目录 `lansan_merged.dict.yaml`。两份原表不作修改。

## 万象词频

词组排序采用 [amzxyz/rime-wanxiang-data](https://github.com/amzxyz/rime-wanxiang-data/tree/722eb52b5c233dbe136ffcb3942eee32d02082b4) 的固定版本 `722eb52b5c233dbe136ffcb3942eee32d02082b4`，作者为 amzxyz 及该项目贡献者。使用 `dicts/` 中的 `jichu`、`duoyin`、`diming`、`mingren`、`yiren` 五张词表；不导入万象拼音编码、语法模型或工具代码。

上游原创词库按 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 许可，完整文本随附在 [LICENSE.wanxiang](LICENSE.wanxiang)。适用范围见该版本的 [LICENSE-SCOPE.md](https://github.com/amzxyz/rime-wanxiang-data/blob/722eb52b5c233dbe136ffcb3942eee32d02082b4/LICENSE-SCOPE.md)。本仓库对数据的修改是：仅提取现有蓝三词组的词频，去掉拼音，同词多音或跨表重复时取最大权重。权重经过上游变换，不视为原始语料出现次数，也不相加。

`wanxiang_frequency.txt` 为可离线使用的提取结果（词条、上游权重两列），`wanxiang-source.json` 记录版本、输入文件及 SHA-256。现有公共词组共有 **167,904** 个（**167,945** 条词组编码记录），其中 **144,009** 个有万象显式权重，覆盖 **85.77%**；**23,895** 个未覆盖词仍然保留。缺少显式权重的上游记录不当作已覆盖。

选择前也对照了白霜版本 `d6214cafa4aacf9c69d2d739d8af31d6c4614eb9` 的 `base`、`ext`、`tencent` 三表，覆盖 131,562 个现有词组（78.36%）。这只是对本仓库词组的覆盖率比较，不是输入法总体质量评测；最终没有混用白霜权重。

## 排序规则

- 官方单字的编码、记录顺序和原有权重状态保持不变。
- 词组权重统一为“万象权重 + 1”；未覆盖词组为 `1`。加一仅保证零权重与正权重的相对次序，同时保留全部低频词。
- 同一个词的所有蓝三编码使用相同万象权重，编码仍取自蓝三原表。
- 万象权重相同（含未覆盖词）时，按原 `ls_ci` 权重降序、再按原记录顺序排列；原官方补充词维持原相对顺序。旧词频只用于并列时的次序，不与万象权重混加。
- 不增加、删除词组，不改重码分组；个人词库仍由可选本机入口导入。

## 再生成

日常准备或部署直接读取已提交的词频子集，无需网络。重新提取该固定版本的子集：

```sh
# 先将指定版本的上游数据仓库下载到本地；脚本校验五个文件的 SHA-256
python3 scripts/update_lansan_frequency.py --source-dir /path/to/rime-wanxiang-data
python3 scripts/prepare.py
```

更新上游版本时，同时更新 `wanxiang-source.json` 中的版本和各文件校验值，重新提取并生成公共词库，检查实际候选变化后提交来源信息、子集和公共生成表。手机直接部署源码中的生成表，不需要运行这些脚本。
