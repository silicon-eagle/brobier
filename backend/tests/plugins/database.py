from collections.abc import Generator

import pytest
from brobier.db.engine import get_admin_engine, get_app_engine
from brobier.db.init_db import db_drop, init_db
from brobier.seeds.seed import check_is_seeded, seed_database
from loguru import logger
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError


@pytest.fixture(scope='session')
def database(setup_environment: bool) -> Generator[None]:
    _ = setup_environment
    logger.debug('Initializing database...')
    admin_engine = get_admin_engine()
    app_engine = get_app_engine()
    try:
        init_db(engine=admin_engine)
    except OperationalError as exc:
        pytest.skip(f'Database is not reachable for DB-backed tests: {exc}')

    existing = set(inspect(admin_engine).get_table_names())
    assert {'users', 'beer_entries'}.issubset(existing), 'Tables not created correctly!'
    logger.debug('Database initialized!')

    logger.debug('Seeding database...')
    seed_database(engine=app_engine)
    assert all(check_is_seeded(engine=app_engine).values()), 'Database not seeded correctly!'

    yield

    logger.debug('Dropping database...')
    db_drop(admin_engine)
    assert not set(inspect(admin_engine).get_table_names()), 'Tables not dropped correctly!'
    logger.debug('Database dropped!')
