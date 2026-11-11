-- 与虎码共用 extended_char：true 为常用字，false 为全字集。
-- 额外隔离补充表，确保其中被 core2022 收录的字也不会改变常用模式。
local function init(env)
  env.extensions = ReverseDb("build/flypy_ext.reverse.bin")
end

local function filter(input, env)
  local common_only = env.engine.context:get_option("extended_char")
  for cand in input:iter() do
    if not common_only or utf8.len(cand.text) ~= 1
        or env.extensions:lookup(cand.text) == "" then
      yield(cand)
    end
  end
end

return { init = init, func = filter }
