from fastapi import APIRouter, HTTPException, status

from backend.schemas.admin import AdminBeerEntryOut

router = APIRouter(tags=['admin:beers'])


@router.get('', response_model=list[AdminBeerEntryOut])
def list_all_beers() -> list[AdminBeerEntryOut]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')
