from backend.app.cli import set_role
from backend.app.db.enums import UserRole
from backend.tests.conftest import auth_headers
from backend.tests.test_rag import WIND, add_document
from backend.tests.test_documents import upload


async def make_admin(client, email="admin@example.com"):
    headers = await auth_headers(client, email)
    await set_role(email, UserRole.ADMIN)
    return headers


async def share(client, headers, document_id, is_shared=True):
    return await client.patch(
        f"/documents/{document_id}",
        headers=headers,
        json={"is_shared": is_shared},
    )


async def test_regular_user_cannot_share(client):
    headers = await auth_headers(client)
    document_id = (await upload(client, headers)).json()["id"]

    response = await share(client, headers, document_id)

    assert response.status_code == 403


async def test_shared_document_is_visible_and_searchable_but_read_only(client):
    admin = await make_admin(client)
    user = await auth_headers(client, "user@example.com")
    document_id = await add_document(client, admin, "wind.txt", WIND)

    shared = await share(client, admin, document_id)

    assert shared.status_code == 200
    assert shared.json()["is_shared"] is True

    listed = await client.get("/documents", headers=user)
    fetched = await client.get(f"/documents/{document_id}", headers=user)
    found = await client.post("/search", headers=user, params={"query": "гарантия на ветрогенераторы"})
    deleted = await client.delete(f"/documents/{document_id}", headers=user)
    reshared = await client.patch(f"/documents/{document_id}", headers=user, json={"is_shared": False})

    assert [document["id"] for document in listed.json()] == [document_id]
    assert fetched.status_code == 200
    assert [result["text"] for result in found.json()] == [WIND]
    assert deleted.status_code == 403
    assert reshared.status_code == 403


async def test_unshared_document_disappears_for_others(client):
    admin = await make_admin(client)
    user = await auth_headers(client, "user@example.com")
    document_id = await add_document(client, admin, "wind.txt", WIND)
    await share(client, admin, document_id)

    await share(client, admin, document_id, is_shared=False)

    assert (await client.get("/documents", headers=user)).json() == []
    assert (await client.post("/search", headers=user, params={"query": "гарантия"})).json() == []


async def test_admin_cannot_share_someone_elses_document(client):
    admin = await make_admin(client)
    user = await auth_headers(client, "user@example.com")
    document_id = (await upload(client, user)).json()["id"]

    response = await share(client, admin, document_id)

    assert response.status_code == 404
