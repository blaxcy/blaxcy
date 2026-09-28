from unittest.mock import patch

from blaxcy.commands import execute


def test_mouse_click():
    with patch("blaxcy.commands.click") as click:
        result = execute(
            {"type": "command", "action": "mouse.click", "x": 10, "y": 20},
            100,
            100,
        )
        click.assert_called_once_with(10, 20, "left", 1)
        assert result["ok"] is True


def test_coordinates_are_bounded():
    try:
        execute({"type": "command", "action": "mouse.move", "x": 100, "y": 0}, 100, 100)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-bounds command accepted")
