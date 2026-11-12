-- 同一个方案调用原单字表或原字词表，保留两套表各自的权重和个人词条。
local M = {}

function M.init(env)
  env.characters = Component.Translator(env.engine, "", "table_translator@translator")
  env.words = Component.Translator(env.engine, Schema("tigress"), "", "table_translator@translator")
end

function M.func(input, segment, env)
  local translator = env.engine.context:get_option("dz_ci") and env.characters or env.words
  local translation = translator:query(input, segment)
  if translation then
    for candidate in translation:iter() do
      yield(candidate)
    end
  end
end

function M.fini(env)
  env.characters = nil
  env.words = nil
end

return M
