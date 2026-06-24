import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from brobier.core.security import decrypt_field, encrypt_field
from brobier.db.engine import get_app_engine
from brobier.db.models import BeerEntry, UserRating
from brobier.schemas.beer import BeerEntryCreate, BeerEntryOut, BeerEntryUpdate
from brobier.schemas.user_rating import UserRatingCreate, UserRatingOut, UserRatingUpdate


def _make_beer_out(beer: BeerEntry) -> BeerEntryOut:
    return BeerEntryOut(
        id=beer.id,
        user_id=beer.user_id,
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


def get_beers_for_user(user_id: uuid.UUID) -> list[BeerEntryOut]:
    with Session(get_app_engine()) as db:
        beers = db.scalars(select(BeerEntry).filter_by(user_id=user_id)).all()
        return [_make_beer_out(beer) for beer in beers]


def create_beer(user_id: uuid.UUID, body: BeerEntryCreate) -> BeerEntryOut:
    with Session(get_app_engine()) as db:
        beer = BeerEntry(
            user_id=user_id,
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
        return _make_beer_out(beer)


def update_beer(beer_id: int, user_id: uuid.UUID, body: BeerEntryUpdate) -> BeerEntryOut:
    with Session(get_app_engine()) as db:
        beer = db.scalar(select(BeerEntry).filter_by(id=beer_id, user_id=user_id))
        if not beer:
            raise ValueError('Beer not found.')

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
        return _make_beer_out(beer)


def delete_beer(beer_id: int, user_id: uuid.UUID) -> None:
    with Session(get_app_engine()) as db:
        beer = db.scalar(select(BeerEntry).filter_by(id=beer_id, user_id=user_id))
        if not beer:
            raise ValueError('Beer not found.')
        db.delete(beer)
        db.commit()


def create_rating(beer_id: int, user_id: uuid.UUID, body: UserRatingCreate) -> UserRatingOut:
    with Session(get_app_engine()) as db:
        beer = db.scalar(select(BeerEntry).filter_by(id=beer_id))
        if not beer:
            raise ValueError('Beer not found.')

        existing = db.scalar(select(UserRating).filter_by(user_id=user_id, beer_entry_id=beer_id))
        if existing:
            raise ValueError('Rating already exists.')

        rating = UserRating(
            user_id=user_id,
            beer_entry_id=beer_id,
            rating=body.rating,
            comment=body.comment,
            drank_at=body.drank_at,
        )
        db.add(rating)
        db.commit()
        db.refresh(rating)
        return UserRatingOut.model_validate(rating)


def update_rating(beer_id: int, user_id: uuid.UUID, body: UserRatingUpdate) -> UserRatingOut:
    with Session(get_app_engine()) as db:
        rating = db.scalar(select(UserRating).filter_by(user_id=user_id, beer_entry_id=beer_id))
        if not rating:
            raise ValueError('Rating not found.')

        if body.rating is not None:
            rating.rating = body.rating
        if body.comment is not None:
            rating.comment = body.comment
        if body.drank_at is not None:
            rating.drank_at = body.drank_at

        db.commit()
        db.refresh(rating)
        return UserRatingOut.model_validate(rating)


def delete_rating(beer_id: int, user_id: uuid.UUID) -> None:
    with Session(get_app_engine()) as db:
        rating = db.scalar(select(UserRating).filter_by(user_id=user_id, beer_entry_id=beer_id))
        if not rating:
            raise ValueError('Rating not found.')
        db.delete(rating)
        db.commit()
