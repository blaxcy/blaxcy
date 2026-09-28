from blaxcy.pairing import create_pairing, fingerprint


def test_pairing_is_unique():
    a = create_pairing()
    b = create_pairing()
    assert a.device_id != b.device_id
    assert a.session_id != b.session_id
    assert a.token != b.token
    assert fingerprint(a.token) != fingerprint(b.token)
