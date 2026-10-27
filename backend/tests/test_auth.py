from backend.tests.conftest import PASSWORD, register


async def test_register_returns_tokens_and_user(client):
    data = await register(client, "new@example.com")

    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "new@example.com"
    assert data["user"]["role"] == "user"


async def test_register_duplicate_email(client):
    await register(client, "dup@example.com")

    response = await client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": PASSWORD},
    )

    assert response.status_code == 409


async def test_login(client):
    await register(client, "login@example.com")

    response = await client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "login@example.com"


async def test_login_wrong_password(client):
    await register(client, "login@example.com")

    response = await client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


async def test_me_requires_access_token(client):
    tokens = await register(client, "me@example.com")

    ok = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    with_refresh = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    anonymous = await client.get("/auth/me")

    assert ok.status_code == 200
    assert ok.json()["email"] == "me@example.com"
    assert with_refresh.status_code == 401
    assert anonymous.status_code == 401


async def test_refresh_accepts_only_refresh_token(client):
    tokens = await register(client, "refresh@example.com")

    ok = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    with_access = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["access_token"]},
    )

    assert ok.status_code == 200
    assert with_access.status_code == 401
