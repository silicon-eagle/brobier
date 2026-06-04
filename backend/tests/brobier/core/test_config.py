import pytest
from brobier.core.config import get_settings


@pytest.mark.usefixtures('needs_env_vars')
def test_get_settings() -> None:
    settings = get_settings()
    assert settings.beer_encryption_key is not None
    assert settings.db_host == 'localhost'
    assert settings.db_name is not None
    assert settings.db_user is not None
    assert isinstance(settings.database_url, str)
    assert 'postgresql+psycopg' in settings.database_url
    assert 'localhost' in settings.database_url
    assert len(settings.cors_origins) >= 1
