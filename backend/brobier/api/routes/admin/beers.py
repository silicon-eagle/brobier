from fastapi import APIRouter

from brobier.schemas.admin import AdminBeerEntryOut
from brobier.services.beers_service import list_all_beers

router = APIRouter(tags=['admin:beers'])


@router.get('', response_model=list[AdminBeerEntryOut])
def admin_list_all_beers(year: int | None = None) -> list[AdminBeerEntryOut]:
    return list_all_beers(year)
