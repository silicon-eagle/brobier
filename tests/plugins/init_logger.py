import time
from collections.abc import Generator

import pytest
from loguru import logger
from tests.backend.setup_logger import setup_logger


def _setup_logger() -> None:
    setup_logger()


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    config_name = config.inipath
    _setup_logger()
    logger.info(f'Started logging! 🔥 ({config_name})')


@pytest.fixture(autouse=True)
def log_test_start_end(request: pytest.FixtureRequest) -> Generator[None]:
    nodeid = request.node.nodeid
    logger.info(f'🚀 STARTING TEST: {nodeid}')
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start

    status = 'UNKNOWN'
    emoji = '❓'
    rep_call = getattr(request.node, 'rep_call', None)
    rep_setup = getattr(request.node, 'rep_setup', None)

    if rep_call is not None:
        if rep_call.skipped:
            status, emoji = 'SKIPPED', '⏭️'
        elif rep_call.passed:
            status, emoji = 'PASSED', '✅'
        else:
            status, emoji = 'FAILED', '❌'
    else:
        if rep_setup is not None and rep_setup.failed:
            status, emoji = 'ERROR (setup)', '⚠️'
        elif rep_setup is not None and rep_setup.skipped:
            status, emoji = 'SKIPPED (setup)', '⏭️'

    logger.info(f'{emoji} FINISHED TEST: {nodeid} | {status} | ⏱️ {elapsed:.2f}s')
