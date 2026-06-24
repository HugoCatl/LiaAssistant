"""
Conversor de Markdown a HTML de Qt (rich text) para las respuestas de Lia.

Qt soporta un subconjunto de HTML; este conversor cubre lo que de verdad usa el
modelo: negritas, cursivas, codigo en linea, bloques de codigo, encabezados,
listas y enlaces. Asi se acaban los ** y * en crudo en el panel.
"""
import html
import re

from src.gui import styles


def _inline(s: str) -> str:
    """Formato en linea (sobre texto ya escapado): codigo, negrita, cursiva, enlaces."""
    s = html.escape(s)
    s = re.sub(
        r"`([^`]+)`",
        lambda m: f'<code style="background:{styles.CODE_BG};color:{styles.CODE_FG};'
                  f'padding:1px 5px;border-radius:4px;">{m.group(1)}</code>',
        s,
    )
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"__([^_]+)__", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        rf'<a href="\2" style="color:{styles.ACCENT_SOFT};">\1</a>',
        s,
    )
    return s


def _blocks(segment: str) -> str:
    """Procesa lineas: encabezados, listas y parrafos."""
    out = []
    in_list = False
    for raw in segment.split("\n"):
        stripped = raw.strip()
        if not stripped:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("<br/>")
            continue

        h = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if h:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(
                f'<b style="color:{styles.TEXT};font-size:14px;">{_inline(h.group(2))}</b><br/>'
            )
            continue

        li = re.match(r"^[-*•]\s+(.*)$", stripped)
        if li:
            if not in_list:
                out.append('<ul style="margin:2px 0;">')
                in_list = True
            out.append(f"<li>{_inline(li.group(1))}</li>")
            continue

        num = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if num:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<b>{num.group(1)}.</b> {_inline(num.group(2))}<br/>")
            continue

        if in_list:
            out.append("</ul>")
            in_list = False
        out.append(f"{_inline(stripped)}<br/>")

    if in_list:
        out.append("</ul>")
    return "".join(out)


def markdown_to_html(text: str) -> str:
    """Convierte una respuesta en Markdown a HTML compatible con QTextBrowser."""
    if not text:
        return ""
    parts = re.split(r"```(.*?)```", text, flags=re.DOTALL)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:  # bloque de codigo
            code = html.escape(part.strip("\n"))
            out.append(
                f'<pre style="background:{styles.CODE_BG};color:{styles.CODE_FG};'
                f'padding:8px 10px;border-radius:6px;white-space:pre-wrap;">{code}</pre>'
            )
        else:
            out.append(_blocks(part))
    return "".join(out)
