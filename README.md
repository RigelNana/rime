# Rime 个人配置

开箱即用的跨平台 Rime 输入法配置，支持 **Fcitx5（Linux）**、**元书 / Hamster（iOS）**、**小狼毫（Windows）** 与 **鼠须管（macOS）**。

仓库已内置所有公共词库、Lua 插件与 OpenCC 转换表，**下载即可直接部署，无需在手机或目标设备上运行脚本**（需要客户端支持 `librime-lua`）。

---

## 包含方案

| 方案名称 | Schema ID | 说明 |
| :--- | :--- | :--- |
| **小鹤音形** | `flypy` | 四码定长、分号快符、可切四码大词库（雾凇 + 萌娘百科）、`&` 组字码打遍扩 J |
| **虎码官方** | `tiger` | 默认纯单字，支持一键切字词混输，覆盖基本区至扩展 I（9.9 万字） |
| **蓝三官方** | `lansanguanfang` | 蓝宝石官方字表 + 万象词频混输，基本区满覆盖，支持 8.2 万字拆分提示 |
| **日本語ローマ字** | `jaroomaji` | 基于 [lazyfoxchan/rime-jaroomaji](https://github.com/lazyfoxchan/rime-jaroomaji) 的日语罗马字方案 |

> 方案顺序与按键习惯在 [default.custom.yaml](default.custom.yaml) 中配置。`flypy_big`、`flypy_ext`、`flypy_yehe`、`tigress`、`PY_c`、`core2022`、`easy_english`、`stroke` 等为内部依赖，不单独出现在方案选单中。

---

## 快速安装

### iOS（元书 / Hamster）

1. 下载最新源码压缩包：[main.zip](https://github.com/RigelNana/rime/archive/refs/heads/main.zip)
2. 在元书「输入方案」右上角选择 **导入方案**（或使用「下载方案」填入上述链接）。
3. 进入「方案目录切换」，选中解压后包含 `default.custom.yaml` 的目录（通常为 `rime-main`），点击 **重新部署**。
4. 简单验证：小鹤输入 `ni` 出「你」，虎码输入 `n` 出「在」，蓝三输入 `n` 出「你」。

> 建议每次更新时导入到新目录再切换，避免旧编译缓存残留。详细导入步骤可参考[元书官方文档](https://ihsiao.com/apps/hamster/v3/docs/guides/schema/)。

### Linux（Fcitx5-Rime）

```bash
git clone https://github.com/RigelNana/rime.git ~/.local/share/fcitx5/rime
cd ~/.local/share/fcitx5/rime
bash scripts/deploy.sh --reload
```

### Windows（小狼毫）/ macOS（鼠须管）

将仓库内容放到对应的 Rime 用户目录中，右键点击输入法图标执行 **重新部署** 即可。

---

## 功能与快捷键

所有开关均可在 **Rime 方案选单（Switcher）** 中操作：电脑按 `F4` 或 ``Ctrl+` ``，手机直接点客户端菜单。

### 通用快捷键

| 快捷键 / 引导符 | 功能 | 说明 |
| :--- | :--- | :--- |
| `F4` / ``Ctrl+` `` | 打开方案选单 | 切换方案及各项开关 |
| `` ` `` | 拼音反查 | 反查当前方案的编码 |
| `'` | 临时英文 | 输入英文词句，无需切换中英 |
| `=` | 计算器 | 支持基础四则运算，如 `=1+1` |
| `[` / `]` | 重复上屏 | 重复输出上一次上屏的内容 |
| `Ctrl+O` | 简繁切换 | 简体 / 繁体输出 |
| `Ctrl+H` | 常用字 / 全字集 | 控制生僻字与扩展区显示 |
| `Ctrl+U` / `Ctrl+Y` | U 区 / U 编注释 | 候选词旁显示 Unicode 分区与码位 |
| `Ctrl+P` / `Ctrl+I` | 拼音 / Emoji | 候选词旁显示注音或 Emoji |

### 小鹤音形（`flypy`）

* **大词库开关（`Ctrl+Shift+B` 或 Switcher）**：默认使用纯净四码小鹤；开启 **大词库** 后，在保留原库全部候选在前的前提下，追加 **雾凇（83.2 万）+ 萌娘百科二次元（16.2 万）** 四码词，依然保持四码定长与顶功手感，不改整句。
* **`&` 组字码（覆盖基本区至扩展 J，共 10.3 万字）**：遇到不认识读音的生僻字，按 `&` 开头依次输入部件的小鹤双拼即可（例如 `&riyt` → `明`、`&mulb` → `森`、`&hguu` → `丁`）。支持自动补全，且在「常用字」模式下也可直接使用。
* **全字集补充（`Ctrl+H`）**：全字集模式下额外提供 **3.5 万+** 基本区繁体/生僻字与扩展区音形四码；日常默认「常用字」模式完全不受干扰。
* **两种反查独立分开**：
  * **通配反查（`` ` ``）**：无需前缀，输入到一半不知道形码时直接补反引号即可（如 ``` jx`` ```、``` ni`` ```、``` ``rx ```）。
  * **拼音反查（`~`）**：按 `~` 引导全拼反查小鹤编码（如 `~ni` → `你 nirx`）。

### 虎码（`tiger`）与蓝三（`lansanguanfang`）

* **纯单字 / 字词混输（`Ctrl+Shift+D` 或 Switcher）**：
  * **虎码**默认纯单字，切混输后自动切换至词库权重；
  * **蓝三**默认字词混输（融合万象词频、保护 GB2312 最简码前三选、表外字后置），切纯单字时自动恢复官方原字序。
* **蓝三拆分提示（`Ctrl+J` 或 Switcher）**：默认隐藏，开启后单字候选显示「字根 · 全码」（如 `摺〔扌习习白 · shhd〕`），已覆盖 **82,403 字**（含全部 GB2312 及基本区增补 90 字）。

---

## 本机维护与测试

仅在电脑端更新词库或修改规则时需要（依赖 Python 3、Bash、`librime` 与 `librime-lua`）：

```bash
# 准备个人词库模板、重新生成合并词库与拆分表并编译
bash scripts/deploy.sh

# 编译后立即重载本机 Fcitx5-Rime
bash scripts/deploy.sh --reload

# 仅生成词库（不编译）
python3 scripts/prepare.py

# 回归测试：模拟纯净源码下载部署并验证各方案实际候选
python3 tests/check_download.py --worktree
```

---

## 个人词库与目录结构

个人词条与运行缓存已通过 `.gitignore` 排除，不会随 Git 提交：

* **个人词库**：`flypy/flypy.user.dict.yaml`、`flypy/flypy.user.top.dict.yaml`、`lansan_user.dict.yaml`、`tiger.extended.dict.yaml`、`tigress.extended.dict.yaml`、`jaroomaji.user.dict.yaml`
* **本机生成入口**：`local.yaml`、`*.local.dict.yaml`（运行 `scripts/prepare.py` 自动生成；缺失时方案自动回退到公共词库）
* **运行数据**：`build/`、`sync/`、`*.userdb/`、`backups/`、`archive/`

迁移到新设备或手机时，如需保留个人词条，额外复制上述个人词库文件及 `local.yaml`、`*.local.dict.yaml` 即可。

---

## 词库来源与致谢

各方案词库、词频与拆分表的固定版本、处理规则及许可证详见：

* 小鹤扩展字、雾凇 / 萌娘四码大词库与野鹤组字码：[sources/flypy/README.md](sources/flypy/README.md)
* 蓝三官方字词合并规则、万象词频与拆分来源：[sources/lansan/README.md](sources/lansan/README.md)
* 公共基础配置来源：[sources/prelude/](sources/prelude/)
