import uuid
from collections.abc import Generator

import pytest
from brobier.db.engine import get_app_engine
from brobier.db.models import User
from brobier.db.models.user import UserRole
from brobier.schemas.admin import AdminUserOut, UserCreate, UserUpdate
from brobier.services.user_service import (
    activate_user,
    create_user,
    deactivate_user,
    list_users,
    update_user,
)
from sqlalchemy import delete
from sqlalchemy.orm import Session

_USER_CREATE = UserCreate(
    email='test-service-user@brobier.local',
    display_name='Service Test User',
    role=UserRole.user,
    is_active=True,
)


@pytest.fixture
def user(database: None) -> Generator[AdminUserOut]:  # noqa: ARG001
    created = create_user(_USER_CREATE)
    yield created
    with Session(get_app_engine()) as db:
        db.execute(delete(User).filter_by(id=created.id))
        db.commit()


@pytest.mark.usefixtures('database')
class TestUserService:
    def test_list_users_returns_seeded_users(self) -> None:
        users = list_users()

        assert len(users) >= 1
        assert all(isinstance(u, AdminUserOut) for u in users)

    def test_create_user_returns_user_out(self) -> None:
        created = create_user(_USER_CREATE)

        try:
            assert isinstance(created, AdminUserOut)
            assert created.email == _USER_CREATE.email
            assert created.display_name == _USER_CREATE.display_name
            assert created.role == UserRole.user
            assert created.is_active is True
        finally:
            with Session(get_app_engine()) as db:
                db.execute(delete(User).filter_by(id=created.id))
                db.commit()

    def test_update_user_changes_fields(self, user: AdminUserOut) -> None:
        updated = update_user(user.id, UserUpdate(display_name='Updated Name', role=UserRole.admin))

        assert updated.display_name == 'Updated Name'
        assert updated.role == UserRole.admin

    def test_update_user_raises_for_unknown_id(self) -> None:
        with pytest.raises(ValueError, match=r'User not found\.'):
            update_user(uuid.uuid4(), UserUpdate(display_name='Ghost'))

    def test_activate_user_sets_is_active_true(self, user: AdminUserOut) -> None:
        deactivate_user(user.id)

        activated = activate_user(user.id)

        assert activated.is_active is True

    def test_deactivate_user_sets_is_active_false(self, user: AdminUserOut) -> None:
        deactivated = deactivate_user(user.id)

        assert deactivated.is_active is False

    def test_activate_user_raises_for_unknown_id(self) -> None:
        with pytest.raises(ValueError, match=r'User not found\.'):
            activate_user(uuid.uuid4())

    def test_deactivate_user_raises_for_unknown_id(self) -> None:
        with pytest.raises(ValueError, match=r'User not found\.'):
            deactivate_user(uuid.uuid4())
