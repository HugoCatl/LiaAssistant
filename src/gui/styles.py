"""
Tokens y hojas de estilo compartidos de LIA.

Centraliza la paleta y los estilos de tarjeta/botón/entrada para que el
onboarding, el panel principal y la burbuja proactiva tengan el mismo lenguaje
visual (glassmorphism violeta). Si quieres cambiar el acento, hazlo aquí.
"""

# --- Paleta -----------------------------------------------------------------
ACCENT = "#C084FC"          # violeta marca
ACCENT_SOFT = "#E9D5FF"     # lila claro (texto sobre acento)
TEXT = "#F1F5F9"            # texto principal
TEXT_DIM = "rgba(255, 255, 255, 0.55)"
CARD_BG = "rgba(22, 16, 28, 0.96)"
CARD_BORDER = "rgba(192, 132, 252, 0.32)"
FONT = "'Segoe UI', 'Outfit', 'Inter', sans-serif"


# --- Hojas de estilo reutilizables ------------------------------------------
def card_style(object_name: str = "GlassCard", radius: int = 16) -> str:
    """Tarjeta glassmorphic con borde violeta."""
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
            color: {ACCENT};
            font-family: {FONT};
            font-weight: 900;
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
            background-color: rgba(25, 20, 30, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 9px;
            color: {TEXT};
            font-family: {FONT};
            font-size: 13px;
            padding: 8px 10px;
            selection-background-color: rgba(192, 132, 252, 0.4);
        }}
        QLineEdit:focus {{
            border: 1px solid rgba(192, 132, 252, 0.7);
            background-color: rgba(30, 24, 38, 0.8);
        }}
        QLineEdit::placeholder {{ color: rgba(255, 255, 255, 0.35); }}
    """


def primary_button_style() -> str:
    return f"""
        QPushButton {{
            background-color: rgba(192, 132, 252, 0.24);
            border: 1px solid rgba(192, 132, 252, 0.55);
            border-radius: 9px;
            color: {ACCENT_SOFT};
            font-family: {FONT};
            font-size: 12px;
            font-weight: 600;
            padding: 7px 18px;
        }}
        QPushButton:hover {{ background-color: rgba(192, 132, 252, 0.4); }}
        QPushButton:pressed {{ background-color: rgba(192, 132, 252, 0.52); }}
    """


def secondary_button_style() -> str:
    return f"""
        QPushButton {{
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 9px;
            color: rgba(255, 255, 255, 0.6);
            font-family: {FONT};
            font-size: 12px;
            padding: 7px 14px;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.08);
            color: {TEXT};
        }}
    """
