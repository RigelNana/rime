# Rime 配置（元书 / Fcitx5 等）

源码已包含部署所需的公共词库、Lua 和公共配置，**下载后可以直接在元书等 Rime 客户端部署，不需要先运行 Python 或 Bash**。当前维护五个方案：

| 菜单名称 | Schema ID | 主词库 |
| --- | --- | --- |
| 小鹤音形 | `flypy` | `flypy`，原分表在 `flypy/`，另导入生成的 `flypy_ext` |
| 虎码官方单字 | `tiger` | `tiger` |
| 虎码官方词库 | `tigress` | `tigress.full`，导入单字、词组和简词 |
| 蓝三官方 | `lansanguanfang` | `lansan_merged`，官方字表与两套词组合并 |
| 日本語ローマ字 | `jaroomaji` | `jaroomaji` 及其分表 |

启用顺序和切换行为在 `default.custom.yaml` 中维护。`PY_c`、`core2022`、`easy_english`、`flypydz`、`flypy_ext` 和 `stroke` 是反查、字符过滤等功能的依赖；它们不是重复的主输入方案。

## 元书：下载并部署

1. 下载[最新源码 ZIP](https://github.com/RigelNana/rime/archive/refs/heads/main.zip)。
2. 在元书「输入方案」右上角菜单选择「导入方案」，选择 ZIP；也可使用「下载方案」添加上面的下载地址。
3. 进入「方案目录切换」，选中解压后包含 `default.custom.yaml`、`flypy.schema.yaml`、`lua/` 的目录（通常是 `rime-main`），然后重新部署。
4. 选择小鹤，输入 `ni` 应出现「你」；虎码输入 `n` 应出现「在」，蓝三输入 `n` 应出现「你」。

导入方式见[元书官方说明](https://ihsiao.com/apps/hamster/v3/docs/guides/schema/)。建议更新时导入到新目录，再切换方案目录，避免旧配置和编译缓存混用。客户端需要支持 librime-lua。

早期提交 `8515732` 及以前需要先运行电脑上的准备脚本，直接导入当时的源码会因缺词库而没有候选；请重新下载当前版本。

## 目录约定

| 位置 | 用途 | Git 管理 |
| --- | --- | --- |
| 根目录 `*.schema.yaml`、`*.custom.yaml`、公共 `*.dict.yaml` | 当前方案和 Rime 需要按名称查找的资源 | 是 |
| `flypy/` | 小鹤分表 | 公共分表是；个人词条否 |
| `lua/`、`opencc/` | 共用功能与转换资源 | 是 |
| `sources/lansan/` | 蓝三原表、万象词频子集与来源记录 | 是 |
| `sources/flypy/` | 小鹤社区生僻字原表与版本记录 | 是 |
| `sources/prelude/` | 随包公共配置的来源和许可证 | 是 |
| `scripts/`、`tests/` | 准备、部署及源码下载回归检查 | 是 |
| `templates/local/` | 个人词库的空模板 | 是 |
| `lansan_merged.dict.yaml` | 自动生成的蓝三公共合并表 | 是，随源码提供 |
| `flypy_ext.dict.yaml` | 自动提取的小鹤公共扩展表 | 是，随源码提供 |
| `local.yaml`、`*.local.dict.yaml` | 可选的本机个人词库入口和生成表 | 否 |
| `build/` | Rime 编译产物 | 否 |
| `sync/`、`*.userdb/`、`user.yaml`、`installation.yaml` | 同步副本、学习记录、本机状态 | 否 |
| `archive/`、`backups/` | 未启用方案的本地归档、修改前备份 | 否 |

方案入口保留在根目录，避免更改 Rime 的查找规则。未启用的旧蓝三、简单鹤、旧拼音和旧日语方案已经归档到 `archive/standardize-*/`，目录中的清单记录原路径和 SHA-256。归档可用于恢复旧方案，不参与当前部署。

## 电脑维护与部署

手机直接使用公共配置无需运行以下脚本。电脑上的维护脚本需要 Python 3、Bash 和带 Lua 支持的 librime；Fcitx5 重新加载需要 `busctl`。脚本不依赖额外 Python 包。默认配置、标点和笔画依赖已经随源码提供。

```sh
# 创建缺失的个人词库空模板、生成蓝三合并表和小鹤扩展表、编译配置
bash scripts/deploy.sh

# 编译后立即重新加载当前用户的 Fcitx5 Rime
bash scripts/deploy.sh --reload
```

非默认共享资源路径可以通过 `RIME_SHARED_DATA_DIR` 指定。脚本会创建缺失的个人词库空模板，并生成 `local.yaml` 与本机词库入口；已有的个人词库不会被覆盖。没有 `local.yaml` 时，五个方案直接使用公共词库。

只准备词库而暂不编译：

```sh
python3 scripts/prepare.py
```

## 小鹤扩展字与切换

沿用虎码的 `extended_char` 开关。手机使用客户端的 Rime 方案选单，选择“全字集／常用字”或 U 区、U 编；电脑按 **F4** 或 **Ctrl+反引号** 打开选单，正在输入时也可按 **Ctrl+H** 或 **Ctrl+Shift+H** 切换字集。

- **常用字**（默认）：保持原有字集过滤和候选，隐藏全部新增补充字。
- **全字集**：显示原库全部候选，并在相同编码的原有候选之后补充扩展字。仍然只匹配完整编码，不开启编码补全。
- **Ctrl+U** 切换 U 区标注，**Ctrl+Y** 切换 Unicode 编码标注；原来的拼音反查和 `~` 通配反查继续可用。

例如全字集模式下，`aary` 可输入 `𠼞`（U+20F1E，扩展 B 区）。四码唯一候选会自动上屏；需要查看候选注释时可用 `~aary` 反查。

来源、固定版本及提取规则见 [小鹤扩展字来源](sources/flypy/README.md)。生成时跳过原库已有的单字，补充项使用低权重；这是社区扩展表，不代表小鹤官方审定。

## 蓝三合并规则

输入为 `sources/lansan/lansan_guanfang.dict.yaml` 和 `sources/lansan/ls_ci.dict.yaml`，输出为根目录 `lansan_merged.dict.yaml`：

- 单字编码和单字之间的顺序沿用官方字表。
- 字词同码时，保留合并前官方表中每个字与旧词的先后关系；单字之间各段词组按万象词频排序。原表没有的新词放在该编码末个单字之后，参与末段词组排序。
- 没有单字的编码，全部词组按万象词频排序。万象覆盖 144,009 个现有词组（85.77%）；未覆盖的 23,895 个词继续保留，排序时使用低词频兜底。同频时沿用旧词组优先级。
- 混合编码写入明确的组内排序权重，使 `by_weight` 落实上述字词关系；不导入外部字频重排单字。
- 按“词条＋编码”去重，同词异码保留。
- `lansan_user.dict.yaml` 只在可选的本机入口中导入一次。

词频固定版本、许可证、覆盖范围和同频规则见 [蓝三词频来源](sources/lansan/README.md)。更新来源词库后运行准备或部署脚本，将公共生成表与来源改动一并提交。不要直接修改生成表或 `build/` 下的文件。

## 个人词条与版本控制

以下文件保留在本机，由 `.gitignore` 排除；空模板只在文件缺失时创建：

- `lansan_user.dict.yaml`
- `jaroomaji.user.dict.yaml`
- `tiger.extended.dict.yaml`、`tigress.extended.dict.yaml`
- `flypy/flypy.user.dict.yaml`、`flypy/flypy.user.top.dict.yaml`

Git 保存配置和公共词库，迁移个人输入习惯时还需单独复制上述个人词库及需要的 `.userdb` 数据。运行准备脚本后，可将本机 `local.yaml` 和 `*.local.dict.yaml` 一起复制到手机。日语学习词库名称保持 `jaroomaji`。`sync/` 和 `backups/` 也属于本机数据，不包含在 Git 提交中。

## 源码下载回归检查

```sh
# 从 Git 导出全新目录，不运行准备脚本，用空共享资源目录编译并检查实际候选
python3 tests/check_download.py

# 检查已暂存但尚未提交的版本
python3 tests/check_download.py --index
```

检查额外需要 C++ 编译器、librime 开发头文件和 librime-lua 动态库；非默认动态库路径通过 `--lua-library` 指定。检查覆盖五个主方案、蓝三词组首选、小鹤字集切换、反查和 Unicode 注释。

```sh
git status
git diff
git add <修改的配置文件>
git commit -m "说明本次配置变更"
```
