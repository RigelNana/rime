-- 蓝三独立拆分注释：追加到已有拼音/反查注释，不改候选文本和顺序。
local M = {}

function M.init(env)
  env.converter = Opencc("lansan_cf.json")
end

function M.tags_match(seg, env)
  return seg:has_tag("abc") or seg:has_tag("lansanguanfang") or seg:has_tag("reverse_lookup")
end

function M.func(input, env)
  local enabled = env.engine.context:get_option("chaifen")
  for cand in input:iter() do
    if enabled and utf8.len(cand.text) == 1 then
      local split = env.converter:convert(cand.text)
      if split and split ~= cand.text then
        split = split:gsub("&nbsp;", " ")
        local comment = cand.comment or ""
        if comment ~= "" then
          comment = comment .. " "
        end
        yield(ShadowCandidate(cand, cand.type, cand.text, comment .. split, false))
      else
        yield(cand)
      end
    else
      yield(cand)
    end
  end
end

return M
