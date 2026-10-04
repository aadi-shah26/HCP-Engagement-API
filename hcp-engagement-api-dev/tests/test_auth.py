import jwt


def test_health_is_public(client):
    assert client.get('/health').status_code == 200


def test_login_returns_signed_expiring_token(client, app_mod):
    resp = client.post('/auth/login', json={'username': 'demo_provider', 'password': 'demo123'})
    assert resp.status_code == 200
    payload = jwt.decode(resp.get_json()['access_token'],
                         app_mod.app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
    assert payload['sub'] == 'demo_provider'
    assert 'exp' in payload


def test_login_rejects_bad_password(client):
    resp = client.post('/auth/login', json={'username': 'demo_provider', 'password': 'wrong'})
    assert resp.status_code == 401


def test_protected_route_requires_valid_token(client, token):
    assert client.get('/ai/models').status_code == 401
    assert client.get('/ai/models', headers={'Authorization': 'Bearer not-a-jwt'}).status_code == 401
    assert client.get('/ai/models', headers={'Authorization': f'Bearer {token}'}).status_code == 200


def test_token_signed_with_other_key_is_rejected(client):
    forged = jwt.encode({'sub': 'demo_admin', 'role': 'admin', 'user_id': 'user_002', 'exp': 9999999999},
                        'jwt-secret-change-in-production', algorithm='HS256')
    resp = client.get('/ai/models', headers={'Authorization': f'Bearer {forged}'})
    assert resp.status_code == 401


def test_failed_logins_are_rate_limited_per_username(client):
    for _ in range(10):
        assert client.post('/auth/login', json={'username': 'demo_admin', 'password': 'x'}).status_code == 401
    assert client.post('/auth/login', json={'username': 'demo_admin', 'password': 'x'}).status_code == 429
    # Other accounts are unaffected
    assert client.post('/auth/login', json={'username': 'demo_provider', 'password': 'demo123'}).status_code == 200


def test_successful_logins_do_not_count_toward_limit(client):
    for _ in range(15):
        assert client.post('/auth/login', json={'username': 'demo_provider', 'password': 'demo123'}).status_code == 200


def test_literature_search_returns_studies(client, token):
    resp = client.post('/literature/search', headers={'Authorization': f'Bearer {token}'},
                       json={'specialty': 'Cardiology', 'keywords': ['statins'],
                             'max_results': 3, 'enable_ai_analysis': False})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['status'] == 'success'
    assert len(body['data']['studies']) == 3
