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

  local caption_text = pandoc.utils.stringify(image.caption)
  local caption_line = ""
  if caption_text ~= "" then
    caption_line = "\n\\caption{" .. caption_text .. "}"
  end

  local latex_source = "\\begin{figure}[H]\n\\centering\n\\includegraphics"
    .. options_string .. "{" .. image.src .. "}" .. caption_line
    .. "\n\\end{figure}"

  return pandoc.RawBlock("latex", latex_source)
end

function Para(paragraph)
  if FORMAT:match("latex") and #paragraph.content == 1
      and paragraph.content[1].t == "Image" then
    return build_figure_latex(paragraph.content[1])
  end
end
