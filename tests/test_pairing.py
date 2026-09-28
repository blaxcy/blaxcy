from blaxcy.pairing import create_pairing, fingerprint


def test_pairing_is_fresh_and_fingerprint_is_stable():
    a = create_pairing()
    b = create_pairing()
    assert a.token != b.token
    assert a.device_id != b.device_id
    assert fingerprint(a.token) == fingerprint(a.token)
    assert fingerprint(a.token) != fingerprint(b.token)
