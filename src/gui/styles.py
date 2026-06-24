"""
Tokens y hojas de estilo compartidos de LIA.

Centraliza la paleta y los estilos de tarjeta/boton/entrada para que el
onboarding, el panel principal y la burbuja proactiva tengan el mismo lenguaje
visual. Cambia el acento AQUI y se repinta toda la app.

Tema actual: "Grafito Indigo" (sobrio, corporativo).
"""

# --- Paleta (Grafito Indigo) -------------------------------------------------
ACCENT = "#6366F1"           # indigo marca
ACCENT_BRIGHT = "#818CF8"    # indigo claro (hover/realces)
ACCENT_SOFT = "#A5B4FC"      # lila-indigo (texto sobre acento)
ACCENT_EDGE = "#3730A3"      # indigo profundo (borde del orbe)

TEXT = "#E8EAF2"             # texto principal (gris muy claro frio)
TEXT_DIM = "rgba(205, 210, 228, 0.55)"
ONLINE = "#34D399"           # verde estado "en linea"
DANGER = "#F87171"

CARD_BG = "rgba(20, 22, 28, 0.97)"        # grafito frio translucido
CARD_BORDER = "rgba(99, 102, 241, 0.30)"
INPUT_BG = "rgba(12, 14, 20, 0.80)"
INPUT_BG_FOCUS = "rgba(18, 20, 28, 0.90)"

# Burbujas de conversacion
BUBBLE_USER_BG = "rgba(99, 102, 241, 0.16)"
BUBBLE_USER_BORDER = "rgba(129, 140, 248, 0.40)"
BUBBLE_LIA_BG = "rgba(40, 43, 54, 0.85)"
BUBBLE_LIA_BORDER = "rgba(99, 102, 241, 0.18)"
CODE_BG = "rgba(99, 102, 241, 0.16)"
CODE_FG = "#C7D2FE"

FONT = "'Segoe UI', 'Outfit', 'Inter', sans-serif"


# --- Hojas de estilo reutilizables ------------------------------------------
def card_style(object_name: str = "GlassCard", radius: int = 16) -> str:
    return f"""
        QFrame#{object_name} {{
            background-color: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: {radius}px;
        }}
    """


def title_style(size: int = 15) -> str:
    return f"""
        QLabel {{
            color: {TEXT};
            font-family: {FONT};
            font-weight: 800;
            font-size: {size}px;
            letter-spacing: 2px;
            background: transparent;
        }}
    """


def label_style(dim: bool = False) -> str:
    color = TEXT_DIM if dim else TEXT
    return f"""
        QLabel {{
            color: {color};
            font-family: {FONT};
            font-size: 12px;
            background: transparent;
        }}
    """


def input_style() -> str:
    return f"""
        QLineEdit {{
            background-color: {INPUT_BG};
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 9px;
            color: {TEXT};
            font-family: {FONT};
            font-size: 13px;
            padding: 8px 12px;
            selection-background-color: rgba(99, 102, 241, 0.45);
        }}
        QLineEdit:focus {{
            border: 1px solid {ACCENT};
            background-color: {INPUT_BG_FOCUS};
        }}
        QLineEdit::placeholder {{ color: rgba(255, 255, 255, 0.32); }}
    """


def primary_button_style() -> str:
    return f"""
        QPushButton {{
            background-color: rgba(99, 102, 241, 0.22);
            border: 1px solid rgba(99, 102, 241, 0.55);
            border-radius: 9px;
            color: {ACCENT_SOFT};
            font-family: {FONT};
            font-size: 12px;
            font-weight: 600;
            padding: 7px 18px;
        }}
        QPushButton:hover {{ background-color: rgba(99, 102, 241, 0.38); }}
        QPushButton:pressed {{ background-color: rgba(99, 102, 241, 0.50); }}
    """


def secondary_button_style() -> str:
    return f"""
        QPushButton {{
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 9px;
            color: rgba(255, 255, 255, 0.6);
            font-family: {FONT};
            font-size: 12px;
            padding: 7px 14px;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.07);
            color: {TEXT};
        }}
    """
