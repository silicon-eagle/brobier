from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from backend.api.routes import auth, beers, calendar, leaderboard
from backend.api.routes.admin import beers as admin_beers
from backend.api.routes.admin import calendar as admin_calendar
from backend.api.routes.admin import users as admin_users
from backend.auth.dependencies import get_current_user, require_admin
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


@app.get('/health')
@app.get('/healthz')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


app.include_router(auth.router, prefix='/auth')
app.include_router(beers.router, prefix='/beers', dependencies=[Depends(get_current_user)])
app.include_router(calendar.router, prefix='/calendar', dependencies=[Depends(get_current_user)])
app.include_router(leaderboard.router, prefix='/leaderboard', dependencies=[Depends(get_current_user)])
app.include_router(admin_users.router, prefix='/admin/users', dependencies=[Depends(require_admin)])
app.include_router(admin_beers.router, prefix='/admin/beers', dependencies=[Depends(require_admin)])
app.include_router(admin_calendar.router, prefix='/admin/calendar', dependencies=[Depends(require_admin)])
