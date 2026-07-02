import uuid
from collections.abc import AsyncGenerator

import pytest
from brobier.auth.jwt import create_access_token
from brobier.db.engine import get_app_engine
from brobier.db.models import User
from brobier.schemas.admin import AdminUserOut
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session


@pytest.fixture
def admin_token() -> str:
    with Session(get_app_engine()) as db:
        user: User | None = db.scalar(select(User).where(User.email == 'admin@brobier.local'))
        assert user is not None
    return create_access_token(user.id, user.role)


@pytest.fixture
async def admin_user(
    async_client: AsyncClient,
    admin_token: str,
) -> AsyncGenerator[dict]:
    payload = {
        'email': f'admin-route-user-{uuid.uuid4()}@brobier.local',
        'display_name': 'Admin Route User',
        'role': 'user',
        'is_active': True,
    }
    response = await async_client.post('/admin/users', json=payload, headers={'Authorization': f'Bearer {admin_token}'})
    assert response.status_code == 201
    user = response.json()

    yield user

    with Session(get_app_engine()) as db:
        db.execute(delete(User).where(User.id == user['id']))
        db.commit()


@pytest.mark.usefixtures('database')
class TestAdminUsers:
    async def test_list_users(self, async_client: AsyncClient, admin_token: str) -> None:
        response = await async_client.get('/admin/users', headers={'Authorization': f'Bearer {admin_token}'})

        assert response.status_code == 200
        users = [AdminUserOut.model_validate(user) for user in response.json()]
        emails = {user.email for user in users}
        assert {'admin@brobier.local', 'alice@brobier.local', 'bob@brobier.local'}.issubset(emails)

    async def test_list_users_returns_error_missing_token(self, async_client: AsyncClient) -> None:
        response = await async_client.get('/admin/users')

        assert response.status_code == 401

    async def test_create_user(self, admin_user: dict) -> None:
        user = AdminUserOut.model_validate(admin_user)

        assert user.email.endswith('@brobier.local')
        assert user.display_name == 'Admin Route User'
        assert user.role == 'user'
        assert user.is_active is True

    async def test_update_user(self, async_client: AsyncClient, admin_token: str, admin_user: dict) -> None:
        user_id = admin_user['id']
        response = await async_client.put(
            f'/admin/users/{user_id}',
            json={'display_name': 'Updated Route User', 'role': 'admin'},
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert response.status_code == 200
        user = AdminUserOut.model_validate(response.json())
        assert user.display_name == 'Updated Route User'
        assert user.role == 'admin'

    async def test_activate_user(self, async_client: AsyncClient, admin_token: str, admin_user: dict) -> None:
        headers = {'Authorization': f'Bearer {admin_token}'}
        user_id = admin_user['id']
        deactivate_response = await async_client.post(f'/admin/users/{user_id}/deactivate', headers=headers)
        assert deactivate_response.status_code == 200

        response = await async_client.post(f'/admin/users/{user_id}/activate', headers=headers)

        assert response.status_code == 200
        user = AdminUserOut.model_validate(response.json())
        assert user.is_active is True

    async def test_deactivate_user(self, async_client: AsyncClient, admin_token: str, admin_user: dict) -> None:
        user_id = admin_user['id']
        response = await async_client.post(
            f'/admin/users/{user_id}/deactivate',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert response.status_code == 200
        user = AdminUserOut.model_validate(response.json())
        assert user.is_active is False

    async def test_update_user_returns_not_found(self, async_client: AsyncClient, admin_token: str) -> None:
        response = await async_client.put(
            f'/admin/users/{uuid.uuid4()}',
            json={'display_name': 'Ghost'},
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert response.status_code == 404

    async def test_activate_user_returns_not_found(self, async_client: AsyncClient, admin_token: str) -> None:
        response = await async_client.post(f'/admin/users/{uuid.uuid4()}/activate', headers={'Authorization': f'Bearer {admin_token}'})

        assert response.status_code == 404

    async def test_deactivate_user_returns_not_found(self, async_client: AsyncClient, admin_token: str) -> None:
        response = await async_client.post(f'/admin/users/{uuid.uuid4()}/deactivate', headers={'Authorization': f'Bearer {admin_token}'})

        assert response.status_code == 404
