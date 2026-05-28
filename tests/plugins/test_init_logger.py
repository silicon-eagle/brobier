from datetime import datetime
from pathlib import Path

import pytest
from loguru import logger

from plugins.init_logger import pytest_configure


def _get_log_file_path(cwd: Path) -> Path:
    date_str = datetime.now().strftime('%Y-%m-%d')
    return cwd / '.log' / f'{date_str}_logfile.log'


def test_pytest_configure_logs_config_inipath(request: pytest.FixtureRequest) -> None:
    log_file = _get_log_file_path(Path.cwd())
    before_text = log_file.read_text(encoding='utf-8') if log_file.exists() else ''

    pytest_configure(request.config)
    logger.complete()

    assert log_file.exists()

    after_text = log_file.read_text(encoding='utf-8')
    appended_text = after_text[len(before_text) :]

    assert 'Started logging!' in appended_text
    assert f'({request.config.inipath})' in appended_text
