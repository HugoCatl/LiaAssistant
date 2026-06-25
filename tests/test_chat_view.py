"""Tests de la vista de chat con burbujas (streaming, typing, descarte, timestamps)."""
import pytest

from src.gui.components.chat_view import ChatView, ChatBubble


@pytest.fixture
def chat(qapp):
    return ChatView()


def test_user_and_lia_bubbles(chat):
    chat.add_user("hola")
    chat.add_lia("¡buenas! **Hugo**")
    assert len(chat._bubbles) == 2
    assert chat._bubbles[0].role == "user"
    assert chat._bubbles[1].role == "lia"
    assert not chat.is_empty()


def test_typing_indicator_lifecycle(chat):
    chat.begin_lia()
    assert chat._current._typing is True
    assert chat._current.is_empty()
    chat.stream_lia("Hola")
    assert chat._current._typing is False   # el primer token corta el "escribiendo…"
    chat.end_lia("Hola, **listo**.")
    assert chat._current is None


def test_empty_turn_is_discarded(chat):
    chat.add_user("algo")
    before = len(chat._rows)
    chat.begin_lia()
    chat.end_lia("")                        # sin texto -> burbuja descartada
    assert len(chat._rows) == before
    assert all(b.role != "lia" or not b.is_empty() for b in chat._bubbles)


def test_clear_resets(chat):
    chat.add_user("x")
    chat.begin_lia()                        # deja un timer de typing vivo
    chat.clear()
    assert chat.is_empty()
    assert chat._current is None
    assert len(chat._bubbles) == 0


def test_system_lines_do_not_count_as_bubbles(chat):
    chat.add_system("Tokens · total 100", "meta")
    chat.add_system("Sin conexión", "error")
    assert len(chat._bubbles) == 0
    assert len(chat._rows) == 2


def test_markdown_is_rendered_in_lia_bubble(chat):
    chat.add_lia("texto con **negrita**")
    html = chat._bubbles[0].label.text()
    assert "<b>negrita</b>" in html
