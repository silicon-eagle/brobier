from collections.abc import Generator

import pytest
from backend.db.engine import get_engine
from backend.db.init_db import db_drop, init_db
from backend.seeds.seed import check_is_seeded, seed_database
from loguru import logger
from sqlalchemy import inspect


@pytest.fixture(scope='session', autouse=True)
def database(setup_environment: bool) -> Generator[None]:
    _ = setup_environment
    logger.debug('Initializing database...')
    engine = get_engine()
    init_db(engine=engine)

    existing = set(inspect(engine).get_table_names())
    assert {'users', 'beer_entries'}.issubset(existing), 'Tables not created correctly!'
    logger.debug('Database initialized!')

    logger.debug('Seeding database...')
    seed_database(engine=engine)
    assert all(check_is_seeded(engine=engine).values()), 'Database not seeded correctly!'

    yield

    logger.debug('Dropping database...')
    db_drop(engine)
    assert not set(inspect(engine).get_table_names()), 'Tables not dropped correctly!'
    logger.debug('Database dropped!')
