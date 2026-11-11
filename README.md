# Fcitx5 / Rime 配置

本目录直接作为 Fcitx5 的 Rime 用户目录使用。当前维护五个方案：

| 菜单名称 | Schema ID | 主词库 |
| --- | --- | --- |
| 小鹤音形 | `flypy` | `flypy`，原分表在 `flypy/`，另导入生成的 `flypy_ext` |
| 虎码官方单字 | `tiger` | `tiger.extended`，导入 `tiger` |
| 虎码官方词库 | `tigress` | `tigress.extended`，导入虎码词组 |
| 蓝三官方 | `lansanguanfang` | `lansan_merged`，官方字表与两套词组合并 |
| 日本語ローマ字 | `jaroomaji` | `jaroomaji` 及其分表 |

启用顺序和切换行为在 `default.custom.yaml` 中维护。`PY_c`、`core2022`、`easy_english`、`flypydz` 和 `flypy_ext` 是反查、字符过滤等功能的依赖；它们不是重复的主输入方案。

## 目录约定

| 位置 | 用途 | Git 管理 |
| --- | --- | --- |
| 根目录 `*.schema.yaml`、`*.custom.yaml`、公共 `*.dict.yaml` | 当前方案和 Rime 需要按名称查找的资源 | 是 |
| `flypy/` | 小鹤分表 | 公共分表是；个人词条否 |
| `lua/`、`opencc/` | 共用功能与转换资源 | 是 |
| `sources/lansan/` | 蓝三官方原表、标准词频表 | 是 |
| `sources/flypy/` | 小鹤社区生僻字原表与版本记录 | 是 |
| `scripts/` | 准备、合并与部署脚本 | 是 |
| `templates/local/` | 个人词库的空模板 | 是 |
| `lansan_merged.dict.yaml` | 自动生成的蓝三合并表 | 否，可重新生成 |
| `flypy_ext.dict.yaml` | 自动提取的小鹤扩展区补充表 | 否，可重新生成 |
| `build/` | Rime 编译产物 | 否 |
| `sync/`、`*.userdb/`、`user.yaml`、`installation.yaml` | 同步副本、学习记录、本机状态 | 否 |
| `archive/`、`backups/` | 未启用方案的本地归档、修改前备份 | 否 |

方案入口保留在根目录，避免更改 Rime 的查找规则。未启用的旧蓝三、简单鹤、旧拼音和旧日语方案已经归档到 `archive/standardize-*/`，目录中的清单记录原路径和 SHA-256。归档可用于恢复旧方案，不参与当前部署。

## 部署

运行环境需要 Python 3、Bash、Fcitx5 Rime、带 Lua 支持的 librime，以及 `/usr/share/rime-data` 中的公共资源（包含默认配置、笔画方案等）。脚本不依赖额外的 Python 包。

```sh
# 创建缺失的个人词库空模板、生成蓝三合并表和小鹤扩展表、编译配置
bash scripts/deploy.sh

# 编译后立即重新加载当前用户的 Fcitx5 Rime
bash scripts/deploy.sh --reload
```

非默认共享资源路径可以通过 `RIME_SHARED_DATA_DIR` 指定。首次从 Git 恢复时也运行同一命令；已有的个人词库不会被空模板覆盖。

只准备词库而暂不编译：

```sh
python3 scripts/prepare.py
```

## 小鹤扩展字与切换

沿用虎码的 `extended_char` 开关。在小鹤方案中按 **F4** 或 **Ctrl+反引号** 打开 Rime 切换菜单，再选择“全字集／常用字”；正在输入时可按 **Ctrl+H** 或 **Ctrl+Shift+H** 直接切换。

- **常用字**（默认）：保持原有字集过滤和候选，隐藏全部新增补充字。
- **全字集**：显示原库全部候选，并在相同编码的原有候选之后补充扩展字。仍然只匹配完整编码，不开启编码补全。
- **Ctrl+U** 切换 U 区标注，**Ctrl+Y** 切换 Unicode 编码标注；原来的拼音反查和 `~` 通配反查继续可用。

例如全字集模式下，`aary` 可输入 `𠼞`（U+20F1E，扩展 B 区）。四码唯一候选会自动上屏；需要查看候选注释时可用 `~aary` 反查。

来源、固定版本及提取规则见 [小鹤扩展字来源](sources/flypy/README.md)。生成时跳过原库已有的单字，补充项使用低权重；这是社区扩展表，不代表小鹤官方审定。

## 蓝三合并规则

输入为 `sources/lansan/lansan_guanfang.dict.yaml` 和 `sources/lansan/ls_ci.dict.yaml`，输出为根目录 `lansan_merged.dict.yaml`：

- 单字记录沿用官方字表。
- 标准词组保留原始词频；官方补充词的词频设为 `1`，排在标准词组之后。
- 按“词条＋编码”去重，同词异码保留。
- `lansan_user.dict.yaml` 单独导入一次。

更新来源词库后运行部署脚本。不要直接修改生成表或 `build/` 下的文件。

## 个人词条与版本控制

以下文件保留在本机，由 `.gitignore` 排除；空模板只在文件缺失时创建：

- `lansan_user.dict.yaml`
- `jaroomaji.user.dict.yaml`
- `tiger.extended.dict.yaml`、`tigress.extended.dict.yaml`
- `flypy/flypy.user.dict.yaml`、`flypy/flypy.user.top.dict.yaml`

Git 保存配置和公共词库，迁移个人输入习惯时还需单独复制上述个人词库及需要的 `.userdb` 数据。`sync/` 和 `backups/` 也属于本机数据，不包含在 Git 提交中。

```sh
git status
git diff
git add <修改的配置文件>
git commit -m "说明本次配置变更"
```
