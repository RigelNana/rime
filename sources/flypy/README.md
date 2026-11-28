# 小鹤扩展字来源

`rare_chars.txt` 保存社区仓库 [ryan00zou/rime-xhup](https://github.com/ryan00zou/rime-xhup) 的《小鹤生僻字全码.txt》，固定在提交 `a72853f045e6e82d53d06b21bcfae93bfb384bde`。

- [固定版本原文件](https://github.com/ryan00zou/rime-xhup/blob/a72853f045e6e82d53d06b21bcfae93bfb384bde/%E5%B0%8F%E9%B9%A4%E7%94%9F%E5%83%BB%E5%AD%97%E5%85%A8%E7%A0%81.txt)
- 保存时仅将 CRLF 换行统一为 LF，保留原始字码内容和顺序。
- 本地源文件 SHA-256：`293082c7fa7d5c4d176130077636e055cd1aa09b7bf30db680226224b6659684`。

这是社区补充码表，不代表小鹤官方审定；罕用字的读音和取形可能需要逐字核对。

## 生成规则

公共 `flypy_ext.dict.yaml` 随源码提供，手机直接部署即可。维护时运行 `python3 scripts/prepare.py` 或部署脚本，更新公共表，并另外生成仅供本机使用的 `flypy_ext.local.dict.yaml`：

1. 提取 CJK 统一汉字基本区（含繁体与基本区生僻字）及扩展区 A–J 中的单字，当前源表覆盖基本区与 A、B、C、D、E、F、G、I。
2. 公共表递归读取 `flypy.dict.yaml` 的公共分表；本机扩展表另外读取两份个人小鹤词库。已经有编码的字不再补充，生成表自身不作为输入。
3. 编码必须是四个英文字母；统一小写。源表第 27814 行 `䝎 TRUE` 在生成表中写作 `䝎 true`。
4. 按“字＋编码”去重，保留多音字的不同编码；按区块优先级（基本区优先于扩展 A–J）稳定排序，同区块保持来源顺序；权重设为 `1`。
5. 补充表在小鹤主词库最后导入，也供 `~` 通配反查使用；由“全字集／常用字”开关控制显示。

当前公共表跳过原库已有的 945 个源表字，新增 **35,619 字、40,969 条编码**。各区新增字数：基本区 12,715、A 5,892、B 15,505、C 13、D 3、E 3、F 1,486、G 1、I 1。原表更新可能改变公共表数量，个人词库只影响本机扩展表。

更新时应同时记录新的来源提交、文件哈希和字数，并提交公共生成表；不要直接修改生成文件。新增个人单字后重新运行部署脚本，会自动从本机扩展表排除该字。

## 小鹤四码大词库来源（`flypy/flypy.rime_ice.dict.yaml`、`flypy/flypy.moegirl.dict.yaml`）

- 通用大词库：[iDvel/rime-ice](https://github.com/iDvel/rime-ice) 的 `cn_dicts/base.dict.yaml` 与 `cn_dicts/ext.dict.yaml`（GPL-3.0），转换并去重后共 831,582 条。
- 二次元词库：[suiginko/moetype](https://github.com/suiginko/moetype)（`20261025`）的 `toneless_moe.dict.yaml`（萌娘百科），转换并去重后共 162,007 条。
- 转换规则：保持小鹤音形四码定长词规则（二字词双拼＋双拼，三字词声＋声＋双拼，四字及以上前三声＋末声），剔除原小鹤主库已有词条，按词频降序排列。
- 通过 `flypy_big` 依赖方案与 `lua/flypy_mode_translator.lua` 接入，默认关闭（标准词库），可在 Rime 方案选单（Switcher）或 `Ctrl+Shift+B` 随时切换。

## 野鹤组字码来源（`flypy_yehe.dict.yaml`）

- 来源：[qqj-jj/yehe](https://github.com/qqj-jj/yehe)（野鹤）的组字码部分，共 103,902 字（137,531 条编码），覆盖基本区及扩展 A–J。
- 在 `flypy` 方案中通过 `&` 前缀引导使用（如 `&hguu` → `丁`），不受“常用字”字集过滤限制。
