import re

import httpx


def get_last_message_id(mailpit: str) -> str:
    response = httpx.get(f'{mailpit}/message/latest')
    response.raise_for_status()
    return response.json()['ID']


def get_message_by_id(mailpit: str, message_id: str) -> dict:
    response = httpx.get(f'{mailpit}/message/{message_id}')
    response.raise_for_status()
    return response.json()


def extract_code(mailpit: str, message_id: str) -> str:
    msg = get_message_by_id(mailpit=mailpit, message_id=message_id)
    match = re.search(r'login code is:\s*(\d{6})', msg['Text'])
    if match is None:
        raise ValueError(f'Could not extract code from message: {msg}')
    code = str(match.group(1))
    return code
