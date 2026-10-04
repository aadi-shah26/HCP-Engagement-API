import time

import pytest


def connect(app_mod, client, token):
    return app_mod.socketio.test_client(app_mod.app, flask_test_client=client, auth={'token': token})


def wait_for(sock, event, timeout=5.0):
    """Collect received events until `event` arrives"""
    received = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        received += sock.get_received()
        if any(r['name'] == event for r in received):
            return received
        time.sleep(0.02)
    raise AssertionError(f'{event} not received; got {[r["name"] for r in received]}')


def chunks(received, request_id):
    return [r['args'][0]['delta'] for r in received
            if r['name'] == 'analysis_chunk' and r['args'][0]['request_id'] == request_id]


def done_events(received):
    return [r['args'][0] for r in received if r['name'] == 'analysis_done']


STUDY = {'title': 'Statin therapy in HFrEF', 'journal': 'JACC', 'abstract': 'statins reduce LDL'}


@pytest.mark.parametrize('auth', [None, {}, {'token': 'not-a-jwt'}])
def test_socket_requires_valid_token(app_mod, client, auth):
    sock = app_mod.socketio.test_client(app_mod.app, flask_test_client=client, auth=auth)
    assert not sock.is_connected()


def test_socket_connects_with_token(app_mod, client, token):
    sock = connect(app_mod, client, token)
    assert sock.is_connected()
    sock.disconnect()


def test_subscribe_uses_token_identity_not_payload(app_mod, client, token):
    sock = connect(app_mod, client, token)
    sock.emit('subscribe', {'user_id': 'user_002', 'channel': 'alerts'})
    with app_mod.realtime_service._lock:
        assert 'user_002' not in app_mod.realtime_service.active_connections
        assert 'user_001' in app_mod.realtime_service.active_connections
    sock.disconnect()


def test_stream_delivers_chunks_in_order(app_mod, client, token, groq_enabled):
    sock = connect(app_mod, client, token)
    ack = sock.emit('stream_analysis', {'request_id': 'r1', 'studies': [STUDY]}, callback=True)
    assert ack == {'status': 'started', 'request_id': 'r1'}
    received = wait_for(sock, 'analysis_done')
    assert chunks(received, 'r1') == ['Statins ', 'reduce ', 'LDL ', '≥30%.']  # UTF-8 intact
    assert done_events(received) == [{'request_id': 'r1', 'source': 'groq'}]
    sock.disconnect()


@pytest.mark.parametrize('chunked', [True, False], ids=['chunked', 'close-delimited'])
def test_stream_is_incremental_not_buffered(app_mod, client, token, groq_enabled, chunked):
    groq_enabled.chunked = chunked
    groq_enabled.tokens = ['a', 'b', 'c', 'd']
    groq_enabled.delay = 0.3
    sock = connect(app_mod, client, token)
    start = time.time()
    sock.emit('stream_analysis', {'request_id': 'r1', 'studies': [STUDY]})
    first = wait_for(sock, 'analysis_chunk')
    # The first token must arrive well before the full ~1.2s response completes
    assert time.time() - start < 0.8
    assert chunks(first, 'r1')[0] == 'a'
    wait_for(sock, 'analysis_done')
    sock.disconnect()


def test_falls_back_to_rule_based_without_groq(app_mod, client, token):
    sock = connect(app_mod, client, token)
    sock.emit('stream_analysis', {'request_id': 'r1', 'studies': [STUDY], 'keywords': ['statins']})
    received = wait_for(sock, 'analysis_done')
    assert len(chunks(received, 'r1')) == 1
    assert done_events(received) == [{'request_id': 'r1', 'source': 'rule_based_fallback'}]
    sock.disconnect()


def test_mid_stream_failure_reports_error_instead_of_mixing_in_fallback(app_mod, client, token, groq_enabled):
    groq_enabled.fail_after = 2
    sock = connect(app_mod, client, token)
    sock.emit('stream_analysis', {'request_id': 'r1', 'studies': [STUDY]})
    received = wait_for(sock, 'analysis_done')
    assert chunks(received, 'r1') == ['Statins ', 'reduce ']
    assert any(r['name'] == 'analysis_error' for r in received)
    assert done_events(received) == [{'request_id': 'r1', 'source': 'groq_interrupted'}]
    sock.disconnect()


def test_newer_request_supersedes_older_one(app_mod, client, token, groq_enabled):
    groq_enabled.tokens = ['1', '2', '3', '4', '5']
    groq_enabled.delay = 0.2
    sock = connect(app_mod, client, token)
    sock.emit('stream_analysis', {'request_id': 'old', 'studies': [STUDY]})
    time.sleep(0.3)
    sock.emit('stream_analysis', {'request_id': 'new', 'studies': [STUDY]})
    received = wait_for(sock, 'analysis_done')
    time.sleep(0.5)  # let any stray events from the old stream arrive
    received += sock.get_received()
    assert [d['request_id'] for d in done_events(received)] == ['new']
    assert chunks(received, 'new') == ['1', '2', '3', '4', '5']
    assert len(chunks(received, 'old')) < 5  # cancelled partway
    sock.disconnect()
