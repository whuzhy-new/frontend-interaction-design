#!/usr/bin/env python3
"""前端交互线索扫描器（启发式，输出"待确认线索"，不是判决）。

覆盖原生 HTML、JSX/TSX、Vue 模板与 CSS/SCSS。组件库标签（首字母大写，如 <Input>、
<Button>）不做原生语义规则判断——它们的 props 语义由组件库决定，静态扫描只会误报。

用法：
    python3 scan_ui.py <文件或目录> [更多路径...]

已知局限（请写给读者看，不要当成"已覆盖"）：
- 文本切分不是解析器：字符串/注释里形如标签的内容、`a < b` 这类比较运算可能干扰。
- 展开属性（{...props}、v-bind="obj"）无法静态求值，相关规则跳过。
- 不判断祖先与运行时行为；命中一律需人工确认。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MARKUP_EXTS = {".html", ".htm", ".jsx", ".tsx", ".js", ".vue"}
STYLE_EXTS = {".css", ".scss", ".less"}
EXTS = MARKUP_EXTS | STYLE_EXTS
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "out", ".next", "coverage", "vendor", ".cache"}
NON_INTERACTIVE = {"div", "span", "li", "td", "tr", "p", "section", "article",
                   "h1", "h2", "h3", "h4", "h5", "h6", "img", "figure"}
INTERACTIVE_ROLES = {"button", "link", "tab", "menuitem", "menuitemcheckbox",
                     "menuitemradio", "checkbox", "switch", "option", "treeitem"}
FOCUS_RULE = re.compile(r"(outline\s*:\s*(none|0|0px)\b|outline-width\s*:\s*0\b|outline-style\s*:\s*none\b)")


def iter_files(paths):
    for p in paths:
        path = Path(p)
        if path.is_file() and path.suffix.lower() in EXTS:
            yield path
        elif path.is_dir():
            for f in path.rglob("*"):
                if f.suffix.lower() in EXTS and not (set(f.parts) & SKIP_DIRS):
                    yield f


def tags(text: str):
    """极简标签切分：跳过引号内的 > 与 JSX 花括号内的 >。"""
    i, n = 0, len(text)
    while i < n:
        if text[i] != "<" or i + 1 >= n or not (text[i + 1].isalpha() or text[i + 1] == "/"):
            i += 1
            continue
        j, depth, quote = i + 1, 0, None
        while j < n:
            c = text[j]
            if quote:
                if c == quote and text[j - 1] != "\\":
                    quote = None
            elif c in "\"'`":
                quote = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth = max(0, depth - 1)
            elif c == ">" and depth == 0:
                break
            j += 1
        raw = text[i:j + 1]
        if raw.lstrip().startswith("</"):
            i = j + 1
            continue
        m = re.match(r"<\s*([a-zA-Z][\w:.-]*)", raw)
        if m:
            yield i, m.group(1), raw
        i = j + 1


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def clip(raw: str, width: int = 96) -> str:
    s = " ".join(raw.split())
    return s if len(s) <= width else s[: width - 1] + "…"


def attr(a: str, name: str) -> bool:
    return bool(re.search(rf"(?<![\w:-]){name}\s*=", a))


def bound(a: str, name: str) -> bool:
    """Vue/JSX 绑定或展开，无法静态判断。"""
    return bool(re.search(rf"(:|v-bind:){name}\s*=", a)) or "..." in a or "v-bind=" in a


def scan_markup(path: Path, text: str):
    out = []
    ids_with_for = {m.group(1) for m in re.finditer(r"\b(?:htmlFor|for)\s*=\s*[\"']([^\"']+)[\"']", text, re.I)}
    has_form = bool(re.search(r"<\s*form[\s>]", text, re.I))
    has_show_modal = "showModal(" in text

    for pos, name, raw in tags(text):
        if name.startswith("/"):
            continue
        ln = line_of(text, pos)
        a = raw
        lower = name.lower()
        is_library = name[:1].isupper()  # 组件库标签，不做原生语义判断

        has_click = bool(re.search(r"(@click|v-on:click|\son(click|mousedown|touchstart)\s*=)", a))

        if not is_library and lower in NON_INTERACTIVE and has_click:
            role = re.search(r"\brole\s*=\s*[\"']?([\w-]+)", a)
            has_role = bool(role and role.group(1).lower() in INTERACTIVE_ROLES)
            has_tab = attr(a, "tabIndex") or attr(a, "tabindex")
            has_key = bool(re.search(r"(onKeyDown|onKeyUp|onKeyPress|@keydown|@keyup|v-on:keydown)", a, re.I))
            missing = [n for n, ok in (("role", has_role), ("tabIndex", has_tab), ("键盘处理", has_key)) if not ok]
            if missing:
                out.append(("click_without_semantics", path, ln, clip(raw),
                            f"缺少 {'/'.join(missing)}；原生 div/span 不天然可聚焦，键盘用户可能用不了"))

        if not is_library and lower == "a" and not (attr(a, "href") or bound(a, "href")):
            out.append(("anchor_without_href", path, ln, clip(raw),
                        "没有 href：行内语义与键盘行为丢失；纯操作请用 button"))

        if not is_library and lower == "img" and not (attr(a, "alt") or bound(a, "alt")):
            out.append(("img_without_alt", path, ln, clip(raw),
                        "读屏用户得不到信息；装饰图应写 alt=\"\""))

        if not is_library and lower in {"input", "select", "textarea"}:
            type_m = re.search(r"\btype\s*=\s*[\"']?([\w-]+)", a)
            typ = (type_m.group(1).lower() if type_m else "text")
            if typ not in {"hidden", "submit", "button", "reset", "image"}:
                has_name = attr(a, "aria-label") or attr(a, "aria-labelledby") or bound(a, "aria-label")
                id_m = re.search(r"\bid\s*=\s*[\"']([^\"']+)[\"']", a)
                linked = bool(id_m and id_m.group(1) in ids_with_for)
                wrapped = bool(id_m is None and re.search(r"<label[^>]*>\s*$", text[max(0, pos - 120):pos]))
                if not (has_name or linked or wrapped):
                    out.append(("field_without_label", path, ln, clip(raw),
                                "没有 aria-label/labelledby，也没找到 label[for] 或包裹 label；需确认标签关联"))

        if not is_library and lower == "button" and has_form and not attr(a, "type") and not attr(a, "htmlType"):
            out.append(("button_without_type", path, ln, clip(raw),
                        "文件里有原生 form：默认 type=submit，可能误触提交；若不在该 form 内可忽略"))

        if lower == "dialog" and not is_library:
            if not has_show_modal:
                out.append(("dialog_native", path, ln, clip(raw),
                            "原生 dialog 需确认用 showModal() 打开才是模态；show() 是非模态"))
        if re.search(r"\brole\s*=\s*[\"']?(dialog|alertdialog)", a, re.I):
            has_name = attr(a, "aria-label") or attr(a, "aria-labelledby")
            if not has_name:
                out.append(("dialog_without_name", path, ln, clip(raw),
                            "对话框缺少可访问名称：加 aria-labelledby 指向标题，或 aria-label"))
            if not attr(a, "aria-modal"):
                out.append(("dialog_modal_unclear", path, ln, clip(raw),
                            "需确认是否模态：非模态不应加 aria-modal；模态则要有焦点管理与背景隔离"))

        m = re.search(r"\btabIndex\s*=\s*(?:\{\s*(\d+)\s*\}|[\"'](\d+)[\"'])", a) or \
            re.search(r"\btabindex\s*=\s*[\"']?(\d+)", a)
        if m:
            val = m.group(1) or (m.group(2) if m.lastindex and m.lastindex >= 2 else None)
            if val and int(val) > 0:
                out.append(("positive_tabindex", path, ln, clip(raw),
                            "正数 tabindex 会打乱 Tab 顺序；用 0（可聚焦）或 -1（脚本聚焦）"))
    return out


def scan_style(path: Path, text: str):
    out = []
    has_alt_focus = bool(re.search(r":focus[^{]*\{[^}]*(box-shadow|border|background)", text, re.I))
    for m in FOCUS_RULE.finditer(text):
        if has_alt_focus:
            continue
        out.append(("focus_outline_removed", path, line_of(text, m.start()), m.group(0),
                    "移除了焦点轮廓且未在同一文件找到替代焦点样式；键盘用户会丢失位置（需确认）"))
    return out


def main(argv):
    paths = argv[1:]
    if not paths:
        print(__doc__.strip())
        return 2
    files = list(iter_files(paths))
    if not files:
        print("没有找到可扫描的文件。")
        return 1

    findings, markup, style = [], 0, 0
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        if f.suffix.lower() in STYLE_EXTS:
            style += 1
            findings += scan_style(f, text)
        else:
            markup += 1
            findings += scan_markup(f, text)

    print(f"扫描 {len(files)} 个文件（标记 {markup}，样式 {style}），命中 {len(findings)} 条线索。")
    print("线索不是判决：组件库标签已跳过原生语义规则，其余仍需结合上下文确认。\n")
    for rule, file, ln, code, hint in sorted(findings, key=lambda x: (x[0], str(x[1]), x[2])):
        print(f"[{rule}] {file}:{ln}")
        print(f"    {code}")
        print(f"    → {hint}")
    if findings:
        print("\n下一步：逐条确认，按影响定级；无法确认的写成「需确认」，不要直接当问题。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
