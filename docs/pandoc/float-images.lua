-- Force exact-here ([H]) figure placement for images.
--
-- By default, LaTeX floats figures away from their surrounding prose,
-- which is confusing in a step-by-step user guide. Pandoc (as of 2.17)
-- does not expose a "placement" image attribute that its LaTeX writer
-- honors, so this filter instead emits the figure environment directly
-- as raw LaTeX with [H] (exact-here) placement, using the `float`
-- package's H specifier already loaded by docs/latex/trainingDoc.cls.
--
-- Only a standalone image paragraph (Pandoc's usual "implicit figure")
-- is affected; inline images within running text are left untouched.

-- Escape LaTeX special characters so caption text from Markdown cannot
-- break the surrounding raw LaTeX or inject unintended commands. The
-- backslash replacement must run first, otherwise the backslashes
-- introduced by the other replacements would themselves get escaped.
local latex_special_character_escapes = {
  { "\\", "\\textbackslash{}" },
  { "{", "\\{" },
  { "}", "\\}" },
  { "%", "\\%" },
  { "&", "\\&" },
  { "_", "\\_" },
  { "#", "\\#" },
  { "$", "\\$" },
  { "~", "\\textasciitilde{}" },
  { "^", "\\textasciicircum{}" },
}

local function escape_latex_special_characters(text)
  local escaped_text = text
  for _, replacement_pair in ipairs(latex_special_character_escapes) do
    local literal_character, latex_escape_sequence = replacement_pair[1], replacement_pair[2]
    -- Both gsub() calls below are wrapped in parentheses to force a
    -- single return value; gsub's second return value (substitution
    -- count) would otherwise be forwarded as the outer gsub's "max
    -- replacements" argument, since it is the outer call's last argument.
    local literal_character_pattern = (literal_character:gsub("%W", "%%%1"))
    local latex_escape_replacement = (latex_escape_sequence:gsub("%%", "%%%%"))
    escaped_text = escaped_text:gsub(literal_character_pattern, latex_escape_replacement)
  end
  return escaped_text
end

local function build_figure_latex(image)
  local include_options = {}
  if image.attributes.width then
    table.insert(include_options, "width=" .. image.attributes.width)
  end
  if image.attributes.height then
    table.insert(include_options, "height=" .. image.attributes.height)
  end

  local options_string = ""
  if #include_options > 0 then
    options_string = "[" .. table.concat(include_options, ",") .. "]"
  end

  local caption_text = escape_latex_special_characters(pandoc.utils.stringify(image.caption))
  local caption_line = ""
  if caption_text ~= "" then
    caption_line = "\n\\caption{" .. caption_text .. "}"
  end

  -- \detokenize makes the image path catcode-safe (spaces, underscores,
  -- and other special characters) without hand-escaping the filename.
  local latex_source = "\\begin{figure}[H]\n\\centering\n\\includegraphics"
    .. options_string .. "{\\detokenize{" .. image.src .. "}}" .. caption_line
    .. "\n\\end{figure}"

  return pandoc.RawBlock("latex", latex_source)
end

function Para(paragraph)
  if FORMAT:match("latex") and #paragraph.content == 1
      and paragraph.content[1].t == "Image" then
    return build_figure_latex(paragraph.content[1])
  end
end
