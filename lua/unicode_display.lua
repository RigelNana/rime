-- 单字候选的 Unicode 编码提示；开关、快捷键沿用虎码的 udpf_switch。
-- 使用衍生候选保存注释，关闭开关后不会在词典候选上残留 U 编。
local function unicode_display(input, env)
  local enabled = env.engine.context:get_option("udpf_switch")
  for cand in input:iter() do
    if enabled and utf8.len(cand.text) == 1 then
      local code = string.format("U+%04X", utf8.codepoint(cand.text))
      local comment = cand.comment or ""
      if comment ~= "" then
        comment = comment .. " "
      end
      yield(ShadowCandidate(cand, cand.type, cand.text, comment .. code, false))
    else
      yield(cand)
    end
  end
end

return unicode_display
