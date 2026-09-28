from blaxcy.chatgpt import tool_manifest


def test_tool_manifest_is_structured():
    manifest = tool_manifest()
    assert manifest["protocol"].startswith("blaxcy/chatgpt/")
    assert manifest["capabilities"]["eye"]["snapshot"] == "eye_snapshot"
    assert manifest["arbitrary_shell"] is False
