from pathlib import Path

import pytest
from dotenv import load_dotenv
from loguru import logger

# pytest plugins
pytest_plugins = ['plugins.logger', 'plugins.database', 'plugins.mailpit', 'plugins.fastapi', 'plugins.globals']


@pytest.fixture(scope='session', autouse=True)
def test_path() -> Path:
    """Return the path to the `tests` directory."""
    path = Path(__file__).parent
    logger.info(f'Local test path: {path!r}')
    return path


@pytest.fixture(scope='session', autouse=True)
def root_path(test_path: Path) -> Path:
    """Return the path to the project root directory."""
    root_path = test_path.parent
    logger.info(f'Project root path: {root_path!r}')
    return root_path


@pytest.fixture(scope='session', autouse=True)
def setup_environment(root_path: Path) -> bool:
    root_env_file = root_path / '.env'

    loaded_root = load_dotenv(dotenv_path=root_env_file)
    logger.info(f'Environment variables loaded from {root_env_file!r}: {loaded_root}')
    return loaded_root


@pytest.fixture
def needs_env_vars(setup_environment: bool) -> None:
    if not setup_environment:
        pytest.skip('Skipping test because the environment variables could not be loaded from the .env file.')
