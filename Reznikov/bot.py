import logging
from telebot import TeleBot

from config import TELEGRAM_TOKEN, LOGS, COUNT_LAST_MSG
from yandex_gpt import ask_gpt
from speechkit import text_to_speech, speech_to_text
from database import create_database, add_message, select_n_last_messages
from validators import (check_number_of_users, is_gpt_token_limit,
                        is_tts_symbol_limit, is_stt_block_limit)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename=LOGS,
    filemode="a",
    datefmt="%Y-%m-%d %H:%M:%S"
)

create_database()

bot = TeleBot(TELEGRAM_TOKEN)


@bot.message_handler(commands=['start', 'help'])
def help_msg(message):
    bot.send_message(message.from_user.id,
                     "Чтобы приступить к общению, отправь мне голосовое "
                     "сообщение или текст")


@bot.message_handler(commands=['debug'])
def debug(message):
    with open(LOGS, "rb") as f:
        bot.send_document(message.chat.id, f)


@bot.message_handler(commands=['tts'])
def tts_handler(message):
    user_id = message.from_user.id
    bot.send_message(user_id,
                     'Отправь следующим сообщеним текст, чтобы я его озвучил!')
    bot.register_next_step_handler(message, tts)


def tts(message):
    user_id = message.from_user.id
    try:
        text = message.text
        tts_symbols, error_message = is_tts_symbol_limit(message=message, text=text)
        if error_message:
            bot.send_message(user_id, error_message)
            return
        add_message(user_id=user_id, full_message=[text, 'test', 0, tts_symbols, 0])
        status_tts, voice_response = text_to_speech(text)
        if status_tts:
            bot.send_voice(user_id, voice_response, reply_to_message_id=message.id)
        else:
            bot.send_message(user_id, "Возникла ошибка", reply_to_message_id=message.id)
    except Exception as e:
        logging.error(e)
        bot.send_message(message.from_user.id, "Не получилось ответить. Попробуй написать другое сообщение")


# Обрабатываем команду /stt
@bot.message_handler(commands=['stt'])
def stt_handler(message):
    user_id = message.from_user.id
    bot.send_message(user_id,
                     'Отправь голосовое сообщение, чтобы я его распознал!')
    bot.register_next_step_handler(message, stt)


# Переводим голосовое сообщение в текст после команды stt
def stt(message):
    user_id = message.from_user.id
    try:
        if not message.voice:
            bot.send_message(user_id, 'Неверный тип данный. Повторите попытку, введя /stt снова')
            return
        stt_blocks, error_message = is_stt_block_limit(message, message.voice.duration)
        if error_message:
            bot.send_message(user_id, error_message)
            return
        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        status_stt, stt_text = speech_to_text(file)
        if not status_stt:
            bot.send_message(user_id, stt_text)
            return
        add_message(user_id=user_id, full_message=[stt_text, 'test', 0, 0, stt_blocks])
        bot.send_message(user_id, stt_text)
    except Exception as e:
        logging.error(e)
        bot.send_message(user_id, "Не получилось ответить. Попробуй записать "
                                  "другое сообщение, введя /stt снова")


@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        user_id = message.from_user.id
        status_check_users, error_message = check_number_of_users(user_id)
        if not status_check_users:
            bot.send_message(user_id, error_message)
            return
        full_user_message = [message.text, 'user', 0, 0, 0]
        add_message(user_id=user_id, full_message=full_user_message)
        last_messages, total_spent_tokens = select_n_last_messages(user_id,
                                                                   COUNT_LAST_MSG)
        total_gpt_tokens, error_message = is_gpt_token_limit(last_messages,
                                                             total_spent_tokens)
        if error_message:
            bot.send_message(user_id, error_message)
            return
        status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)
        if not status_gpt:
            bot.send_message(user_id, answer_gpt)
            return
        total_gpt_tokens += tokens_in_answer
        full_gpt_message = [answer_gpt, 'assistant', total_gpt_tokens, 0, 0]
        add_message(user_id=user_id, full_message=full_gpt_message)
        bot.send_message(user_id, answer_gpt, reply_to_message_id=message.id)
    except Exception as e:
        logging.error(e)
        bot.send_message(message.from_user.id,
                         "Не получилось ответить. Попробуй написать другое сообщение")


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    try:
        status_check_users, error_message = check_number_of_users(user_id)
        if not status_check_users:
            bot.send_message(user_id, error_message)
            return
        stt_blocks, error_message = is_stt_block_limit(message,
                                                       message.voice.duration)
        if error_message:
            bot.send_message(user_id, error_message)
            return
        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        status_stt, stt_text = speech_to_text(file)
        if not status_stt:
            bot.send_message(user_id, stt_text)
            return
        add_message(user_id=user_id,
                    full_message=[stt_text, 'user', 0, 0, stt_blocks])
        last_messages, total_spent_tokens = select_n_last_messages(user_id,
                                                                   COUNT_LAST_MSG)
        total_gpt_tokens, error_message = is_gpt_token_limit(last_messages,
                                                             total_spent_tokens)
        if error_message:
            bot.send_message(user_id, error_message)
            return
        status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)
        if not status_gpt:
            bot.send_message(user_id, answer_gpt)
            return
        total_gpt_tokens += tokens_in_answer
        tts_symbols, error_message = is_tts_symbol_limit(message=message,
                                                         text=answer_gpt)
        add_message(user_id=user_id,
                    full_message=[answer_gpt, 'assistant', total_gpt_tokens,
                                  tts_symbols, 0])
        if error_message:
            bot.send_message(user_id, error_message)
            return
        status_tts, voice_response = text_to_speech(answer_gpt)
        if status_tts:
            bot.send_voice(user_id, voice_response,
                           reply_to_message_id=message.id)
        else:
            bot.send_message(user_id, answer_gpt,
                             reply_to_message_id=message.id)
    except Exception as e:
        logging.error(e)
        bot.send_message(user_id,
                         "Не получилось ответить. Попробуй записать другое сообщение")


bot.polling()
