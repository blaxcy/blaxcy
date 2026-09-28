import json

from blaxcy.protocol import decode, encode, event, session_token


def test_protocol_roundtrip():
    msg = event("test", value=1)
    assert decode(encode(msg)) == msg


def test_token_is_unique():
    assert session_token() != session_token()
