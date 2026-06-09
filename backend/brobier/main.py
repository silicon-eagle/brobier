from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from brobier.api.routes import auth, beers, calendar, leaderboard
from brobier.api.routes.admin import beers as admin_beers
from brobier.api.routes.admin import calendar as admin_calendar
from brobier.api.routes.admin import users as admin_users
from brobier.auth.dependencies import get_current_user, require_admin
from brobier.db.engine import get_admin_engine, get_app_engine
from brobier.db.init_db import init_db
from brobier.db.utils import Table
from brobier.seeds.seed import seed_database


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator:
    init_db(get_admin_engine())
    seed_database(get_app_engine(), tables=[Table.calendar_entries])
    yield


app = FastAPI(title='Brobier Backend', lifespan=lifespan)


@app.get('/health')
@app.get('/healthz')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


app.include_router(auth.router, prefix='/auth')
app.include_router(leaderboard.router, prefix='/leaderboard')
app.include_router(beers.router, prefix='/beers', dependencies=[Depends(get_current_user)])
app.include_router(calendar.router, prefix='/calendar', dependencies=[Depends(get_current_user)])
app.include_router(admin_users.router, prefix='/admin/users', dependencies=[Depends(require_admin)])
app.include_router(admin_beers.router, prefix='/admin/beers', dependencies=[Depends(require_admin)])
app.include_router(admin_calendar.router, prefix='/admin/calendar', dependencies=[Depends(require_admin)])
