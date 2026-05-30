from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.routes.auth import router as auth_router
from backend.db.engine import get_engine
from backend.db.init_db import init_db
from backend.db.utils import Table
from backend.seeds.seed import seed_database


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator:
    engine = get_engine()
    init_db(engine)
    seed_database(engine, tables=[Table.calendar_entries])
    yield


app = FastAPI(title='Brobier Backend', lifespan=lifespan)
app.include_router(auth_router)


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}
