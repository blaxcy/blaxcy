from unittest.mock import patch

from blaxcy.leader import Leader


def test_leader_clicks_unique_element():
    state = {"elements": [{"id": "e1", "name": "Submit", "x": 10, "y": 20, "width": 100, "height": 40}]}
    leader = Leader(lambda: state)
    with patch("blaxcy.leader.execute") as run:
        run.return_value = {"ok": True}
        result = leader.execute("click Submit", 800, 600)
        run.assert_called_once_with(
            {"type": "command", "action": "mouse.click", "x": 60, "y": 40},
            800,
            600,
        )
        assert result["ok"] is True


def test_leader_rejects_ambiguous_target():
    state = {"elements": [
        {"id": "e1", "name": "Open", "x": 0, "y": 0, "width": 10, "height": 10},
        {"id": "e2", "name": "Open", "x": 20, "y": 20, "width": 10, "height": 10},
    ]}
    leader = Leader(lambda: state)
    try:
        leader.execute("click Open", 100, 100)
    except Exception as exc:
        assert "ambiguous" in str(exc)
    else:
        raise AssertionError("ambiguous target was accepted")


def test_leader_type():
    leader = Leader(lambda: {"elements": []})
    with patch("blaxcy.leader.execute") as run:
        run.return_value = {"ok": True}
        leader.execute("type hello world", 800, 600)
        run.assert_called_once_with(
            {"type": "command", "action": "keyboard.type", "text": "hello world"},
            800,
            600,
        )
