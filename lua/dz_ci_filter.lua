-- 纯单字只限制正常字母编码的码表候选。
-- 临时英文、拼音反查、快符、计算器、日期与重复上屏保留各自行为。
local function filter(input, env)
  local single_char = env.engine.context:get_option("dz_ci")
  local code = env.engine.context.input
  for cand in input:iter() do
    local genuine = cand:get_genuine()
    local ordinary_table = genuine.type == "table" or genuine.type == "user_table"
    local segment_code = code:sub(cand.start + 1, cand._end)
    if not single_char or not ordinary_table
        or not segment_code:match("^[a-z]+$") or utf8.len(cand.text) == 1 then
      yield(cand)
    end
  end
end

return filter
