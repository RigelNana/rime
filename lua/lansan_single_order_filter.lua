-- 混输权重允许表外字跨过规范字；纯单字模式恢复调整前的字序。
local function init(env)
  env.ranks = {}
  for code, chars in pairs(require("lansan_single_order")) do
    local ranks = {}
    local index = 0
    for _, cp in utf8.codes(chars) do
      index = index + 1
      ranks[utf8.char(cp)] = index
    end
    env.ranks[code] = ranks
  end
end

local function filter(input, env)
  local context = env.engine.context
  local ranks = context:get_option("dz_ci") and env.ranks[context.input]
  if not ranks then
    for cand in input:iter() do yield(cand) end
    return
  end
  local all, positions, tables = {}, {}, {}
  for cand in input:iter() do
    all[#all + 1] = cand
    local genuine = cand:get_genuine()
    if (genuine.type == "table" or genuine.type == "user_table")
        and cand.start == 0 and cand._end == #context.input and utf8.len(cand.text) == 1 then
      positions[#positions + 1] = #all
      tables[#tables + 1] = { cand = cand, rank = ranks[cand.text] or math.huge, index = #all }
    end
  end
  table.sort(tables, function(a, b)
    if a.rank ~= b.rank then return a.rank < b.rank end
    return a.index < b.index
  end)
  for i, position in ipairs(positions) do all[position] = tables[i].cand end
  for _, cand in ipairs(all) do yield(cand) end
end

return { init = init, func = filter }
