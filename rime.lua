-- 共用 Lua 入口；schema 中的 @* 模块由 librime-lua 直接加载。
charset_comment_filter = require("charset_comment_filter") --Unicode分区提示
core2022 = require("core2022_filter") --自定义字符集过滤（常用字集）
number_translator = require("number")
calculator_translator = require("calculator_translator")  --简易计算器
exe_processor = require("exe")  -- 网页启动器
shijian2_translator = require("shijian2") -- 高级时间
