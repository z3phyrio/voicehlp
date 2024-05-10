import logging
import math
from config import (LOGS, MAX_USERS, MAX_USER_GPT_TOKENS, MAX_USER_STT_BLOCKS,
                    MAX_USER_TTS_SYMBOLS)
from database import count_users, count_all_limits
from yandex_gpt import count_gpt_tokens

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOGS,
    filemode='a',
    datefmt="%Y-%m-%d %H:%M:%S"
)


def check_number_of_users(user_id):
    count = count_users(user_id)
    if count is None:
        return None, "Ошибка при работе с БД"
    if count > MAX_USERS:
        return None, "Превышено максимальное количество пользователей"
    return True, ""


def is_gpt_token_limit(messages, total_spent_tokens):
    all_tokens = count_gpt_tokens(messages) + total_spent_tokens
    if all_tokens > MAX_USER_GPT_TOKENS:
        return None, f"Превышен общий лимит GPT токенов {MAX_USER_GPT_TOKENS}"
    return all_tokens, ""


def is_stt_block_limit(message, duration):
    user_id = message.from_user.id
    audio_blocks = math.ceil(duration / 15)
    all_blocks = count_all_limits(user_id, "stt_blocks") + audio_blocks
    if duration >= 30:
        return None, "SpeechKit STT работает с голосовыми сообщениями меньше 30 секунд"
    if all_blocks >= MAX_USER_STT_BLOCKS:
        return None, f"Превышен общий лимит SpeechKit STT {MAX_USER_STT_BLOCKS}"
    return audio_blocks, ''


def is_tts_symbol_limit(message, text):
    user_id = message.from_user.id
    text_symbols = len(text)
    all_symbols = count_all_limits(user_id, "tts_symbols") + text_symbols
    if all_symbols >= MAX_USER_TTS_SYMBOLS:
        return None, f"Превышен общий лимит SpeechKit TTS {MAX_USER_TTS_SYMBOLS}"
    return len(text), ''
