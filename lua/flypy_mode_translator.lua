-- 同一个方案调用标准词库或大词库，保留两套表各自的顺序和个人词条。
local M = {}

function M.init(env)
  env.standard = Component.Translator(env.engine, "", "table_translator@translator")
  env.big = Component.Translator(env.engine, Schema("flypy_big"), "", "table_translator@translator")
end

function M.func(input, segment, env)
  local translator = env.engine.context:get_option("flypy_big") and env.big or env.standard
  local translation = translator:query(input, segment)
  if translation then
    for candidate in translation:iter() do
      yield(candidate)
    end
  end
end

function M.fini(env)
  env.standard = nil
  env.big = nil
end

return M
