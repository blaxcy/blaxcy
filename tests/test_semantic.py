import numpy as np

from blaxcy.semantic import SemanticAnalyzer, SemanticConfig


class FakeAccessibility:
    def snapshot(self):
        return [{
            "type": "accessibility",
            "role": "button",
            "name": "Open",
            "x": 10,
            "y": 20,
            "width": 80,
            "height": 30,
            "actionable": True,
        }]


def test_semantic_normalizes_accessibility():
    analyzer = SemanticAnalyzer(SemanticConfig(ocr=False, accessibility=False))
    analyzer.accessibility = FakeAccessibility()
    result = analyzer.analyze(np.zeros((100, 100, 3), dtype=np.uint8))
    assert len(result) == 1
    assert result[0]["id"].startswith("e_")
    assert result[0]["actionable"] is True
    assert result[0]["screen"]["x"] == 10
