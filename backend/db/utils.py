import enum


class Table(enum.StrEnum):
    users = 'users'
    beer_entries = 'beer_entries'
    calendar_entries = 'calendar_entries'
    login_codes = 'login_codes'
    refresh_tokens = 'refresh_tokens'
    user_ratings = 'user_ratings'
