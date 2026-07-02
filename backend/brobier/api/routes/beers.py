from fastapi import APIRouter, Depends, status

from brobier.auth.dependencies import get_current_user
from brobier.db.models.user import User
from brobier.schemas.beer import BeerEntryCreate, BeerEntryOut, BeerEntryUpdate
from brobier.schemas.user_rating import UserRatingCreate, UserRatingOut, UserRatingUpdate
from brobier.services import beers_service

router = APIRouter(tags=['beers'])


@router.get('/me', response_model=list[BeerEntryOut])
def get_my_beers(current_user: User = Depends(get_current_user)) -> list[BeerEntryOut]:
    return beers_service.get_beers_for_user(current_user.id)


@router.post('', response_model=BeerEntryOut, status_code=status.HTTP_201_CREATED)
def create_beer(
    body: BeerEntryCreate,
    current_user: User = Depends(get_current_user),
) -> BeerEntryOut:
    return beers_service.create_beer(current_user.id, body)


@router.put('/{beer_id}', response_model=BeerEntryOut)
def update_beer(
    beer_id: int,
    body: BeerEntryUpdate,
    current_user: User = Depends(get_current_user),
) -> BeerEntryOut:
    return beers_service.update_beer(beer_id, current_user.id, body)


@router.delete('/{beer_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_beer(
    beer_id: int,
    current_user: User = Depends(get_current_user),
) -> None:
    beers_service.delete_beer(beer_id, current_user.id)


@router.post('/{beer_id}/ratings', response_model=UserRatingOut, status_code=status.HTTP_201_CREATED)
def create_rating(
    beer_id: int,
    body: UserRatingCreate,
    current_user: User = Depends(get_current_user),
) -> UserRatingOut:
    return beers_service.create_rating(beer_id, current_user.id, body)


@router.put('/{beer_id}/ratings/me', response_model=UserRatingOut)
def update_rating(
    beer_id: int,
    body: UserRatingUpdate,
    current_user: User = Depends(get_current_user),
) -> UserRatingOut:
    return beers_service.update_rating(beer_id, current_user.id, body)


@router.delete('/{beer_id}/ratings/me', status_code=status.HTTP_204_NO_CONTENT)
def delete_rating(
    beer_id: int,
    current_user: User = Depends(get_current_user),
) -> None:
    beers_service.delete_rating(beer_id, current_user.id)
