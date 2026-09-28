from blaxcy.semantic import SemanticAnalyzer


def test_semantic_ids_are_stable():
    analyzer = SemanticAnalyzer()
    element = {
        "type": "accessibility",
        "role": "button",
        "name": "Save",
        "x": 10,
        "y": 20,
        "width": 80,
        "height": 30,
    }
    first = analyzer._stable_id(element)
    second = analyzer._stable_id(dict(element))
    assert first == second
    assert first.startswith("e_")
