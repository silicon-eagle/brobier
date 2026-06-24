from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session

from brobier.core.security import decrypt_field
from brobier.db.engine import get_admin_engine
from brobier.db.models import BeerEntry
from brobier.schemas.admin import AdminBeerEntryOut

router = APIRouter(tags=['admin:beers'])


def _parse_admin_beer(beer: BeerEntry) -> AdminBeerEntryOut:
    return AdminBeerEntryOut(
        id=beer.id,
        user_id=beer.user_id,
        display_name=beer.user.display_name,
        year=beer.year,
        beer_name=decrypt_field(beer.beer_name_encrypted),
        brewery=decrypt_field(beer.brewery_encrypted),
        untappd_url=decrypt_field(beer.untappd_url_encrypted) if beer.untappd_url_encrypted else None,
        comment=decrypt_field(beer.comment_encrypted) if beer.comment_encrypted else None,
        bought_from=beer.bought_from,
        bought_at=beer.bought_at,
        created_at=beer.created_at,
        updated_at=beer.updated_at,
    )


@router.get('', response_model=list[AdminBeerEntryOut])
def list_all_beers(year: int | None = None) -> list[AdminBeerEntryOut]:
    with Session(get_admin_engine()) as db:
        query = select(BeerEntry).order_by(BeerEntry.created_at.desc())
        if year is not None:
            query = query.filter_by(year=year)
        beers = db.scalars(query).all()
        return [_parse_admin_beer(beer) for beer in beers]
