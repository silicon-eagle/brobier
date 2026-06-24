from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from brobier.auth.dependencies import get_current_user
from brobier.core.security import decrypt_field, encrypt_field
from brobier.db.engine import get_app_engine
from brobier.db.models import BeerEntry, UserRating
from brobier.db.models.user import User
from brobier.schemas.beer import BeerEntryCreate, BeerEntryOut, BeerEntryUpdate
from brobier.schemas.user_rating import UserRatingCreate, UserRatingOut, UserRatingUpdate

router = APIRouter(tags=['beers'])


def parse_beer_entries(beer_entry: BeerEntry) -> BeerEntryOut:
    return BeerEntryOut(
        id=beer_entry.id,
        user_id=beer_entry.user_id,
        year=beer_entry.year,
        beer_name=decrypt_field(beer_entry.beer_name_encrypted),
        brewery=decrypt_field(beer_entry.brewery_encrypted),
        untappd_url=decrypt_field(beer_entry.untappd_url_encrypted) if beer_entry.untappd_url_encrypted else None,
        comment=decrypt_field(beer_entry.comment_encrypted) if beer_entry.comment_encrypted else None,
        bought_from=beer_entry.bought_from,
        bought_at=beer_entry.bought_at,
        created_at=beer_entry.created_at,
        updated_at=beer_entry.updated_at,
    )


@router.get('/me', response_model=list[BeerEntryOut])
def get_my_beers(current_user: User = Depends(get_current_user)) -> list[BeerEntryOut]:
    with Session(get_app_engine()) as db:
        user_beers = db.scalars(select(BeerEntry).where(BeerEntry.user_id == current_user.id)).all()
        return [parse_beer_entries(beer) for beer in user_beers]


@router.post('', response_model=BeerEntryOut, status_code=status.HTTP_201_CREATED)
def create_beer(
    body: BeerEntryCreate,
    current_user: User = Depends(get_current_user),
) -> BeerEntryOut:
    with Session(get_app_engine()) as db:
        beer = BeerEntry(
            user_id=current_user.id,
            year=body.year,
            beer_name_encrypted=encrypt_field(body.beer_name),
            brewery_encrypted=encrypt_field(body.brewery),
            untappd_url_encrypted=encrypt_field(body.untappd_url) if body.untappd_url else None,
            comment_encrypted=encrypt_field(body.comment) if body.comment else None,
            bought_from=body.bought_from,
            bought_at=body.bought_at,
        )
        db.add(beer)
        db.commit()
        db.refresh(beer)
        return parse_beer_entries(beer)


@router.put('/{beer_id}', response_model=BeerEntryOut)
def update_beer(
    beer_id: int,
    body: BeerEntryUpdate,
    current_user: User = Depends(get_current_user),
) -> BeerEntryOut:
    with Session(get_app_engine()) as db:
        beer = db.scalar(select(BeerEntry).where(BeerEntry.id == beer_id))
        if not beer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Beer not found.')
        if beer.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Beer not found.')

        if body.year is not None:
            beer.year = body.year
        if body.beer_name is not None:
            beer.beer_name_encrypted = encrypt_field(body.beer_name)
        if body.brewery is not None:
            beer.brewery_encrypted = encrypt_field(body.brewery)
        if body.untappd_url is not None:
            beer.untappd_url_encrypted = encrypt_field(body.untappd_url)
        if body.comment is not None:
            beer.comment_encrypted = encrypt_field(body.comment)
        if body.bought_from is not None:
            beer.bought_from = body.bought_from
        if body.bought_at is not None:
            beer.bought_at = body.bought_at

        db.commit()
        db.refresh(beer)
        return parse_beer_entries(beer)


@router.delete('/{beer_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_beer(
    beer_id: int,
    current_user: User = Depends(get_current_user),
) -> None:
    with Session(get_app_engine()) as db:
        beer = db.scalar(select(BeerEntry).where(BeerEntry.id == beer_id))
        if not beer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Beer not found.')
        if beer.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Beer not found.')
        db.delete(beer)
        db.commit()


@router.post('/{beer_id}/ratings', response_model=UserRatingOut, status_code=status.HTTP_201_CREATED)
def create_rating(
    beer_id: int,
    body: UserRatingCreate,
    current_user: User = Depends(get_current_user),
) -> UserRatingOut:
    with Session(get_app_engine()) as db:
        beer = db.scalar(select(BeerEntry).where(BeerEntry.id == beer_id))
        if not beer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Beer not found.')

        existing = db.scalar(select(UserRating).where(UserRating.user_id == current_user.id, UserRating.beer_entry_id == beer_id))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Rating already exists.')

        rating = UserRating(
            user_id=current_user.id,
            beer_entry_id=beer_id,
            rating=body.rating,
            comment=body.comment,
            drank_at=body.drank_at,
        )
        db.add(rating)
        db.commit()
        db.refresh(rating)
        return UserRatingOut.model_validate(rating)


@router.put('/{beer_id}/ratings/me', response_model=UserRatingOut)
def update_rating(
    beer_id: int,
    body: UserRatingUpdate,
    current_user: User = Depends(get_current_user),
) -> UserRatingOut:
    with Session(get_app_engine()) as db:
        rating = db.scalar(select(UserRating).where(UserRating.user_id == current_user.id, UserRating.beer_entry_id == beer_id))
        if not rating:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Rating not found.')

        if body.rating is not None:
            rating.rating = body.rating
        if body.comment is not None:
            rating.comment = body.comment
        if body.drank_at is not None:
            rating.drank_at = body.drank_at

        db.commit()
        db.refresh(rating)
        return UserRatingOut.model_validate(rating)


@router.delete('/{beer_id}/ratings/me', status_code=status.HTTP_204_NO_CONTENT)
def delete_rating(
    beer_id: int,
    current_user: User = Depends(get_current_user),
) -> None:
    with Session(get_app_engine()) as db:
        rating = db.scalar(select(UserRating).where(UserRating.user_id == current_user.id, UserRating.beer_entry_id == beer_id))
        if not rating:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Rating not found.')
        db.delete(rating)
        db.commit()
