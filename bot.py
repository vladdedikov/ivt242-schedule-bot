"""Личный бот расписания. Python 3.9+, без внешних библиотек."""
import argparse
import datetime as dt
import getpass
import json
import os
from pathlib import Path
import secrets
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
MSK = ZoneInfo('Europe/Moscow')
TIMES = ['08:00–09:30', '09:50–11:20', '11:30–13:00', '13:20–14:50',
         '15:00–16:30', '16:40–18:10', '18:20–19:50']
DAYS = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
MENU = {'keyboard': [[{'text': 'Сегодня'}, {'text': 'Завтра'}],
                     [{'text': 'Выбрать день'}]], 'resize_keyboard': True}


def calendar_week(date):
    monday = date - dt.timedelta(days=date.weekday())
    rows = []
    for index in range(7):
        day = monday + dt.timedelta(days=index)
        rows.append([{'text': f'{DAYS[index]} · {day:%d.%m.%Y}',
                      'callback_data': f'day:{day.isoformat()}'}])
    rows.append([{'text': '← Неделя', 'callback_data': f'week:{(monday - dt.timedelta(days=7)).isoformat()}'},
                 {'text': 'Неделя →', 'callback_data': f'week:{(monday + dt.timedelta(days=7)).isoformat()}'}])
    return {'inline_keyboard': rows}


def handle_update(config, update, today):
    token, chat_id = config['token'], config['chat_id']
    callback = update.get('callback_query')
    if callback:
        if callback.get('message', {}).get('chat', {}).get('id') != chat_id:
            api(token, 'answerCallbackQuery', callback_query_id=callback['id'])
            return
        try:
            action, value = callback.get('data', '').split(':', 1)
            date = dt.date.fromisoformat(value)
            if action not in ('day', 'week'):
                raise ValueError()
        except (ValueError, TypeError):
            api(token, 'answerCallbackQuery', callback_query_id=callback['id'], text='Открой выбор дня заново: /days')
            return
        api(token, 'answerCallbackQuery', callback_query_id=callback['id'])
        if action == 'day':
            api(token, 'sendMessage', chat_id=chat_id, text=format_day(date), reply_markup=MENU)
        else:
            api(token, 'editMessageText', chat_id=chat_id,
                message_id=callback['message']['message_id'], text='Выбери день:', reply_markup=calendar_week(date))
        return
    message = update.get('message', {})
    if message.get('chat', {}).get('id') != chat_id:
        return
    command = message.get('text', '').split('@')[0].strip()
    if command in ('/days', 'Выбрать день'):
        api(token, 'sendMessage', chat_id=chat_id, text='Выбери день:', reply_markup=calendar_week(today))
    elif command in ('/start', '/today', '/tomorrow', 'Сегодня', 'Завтра'):
        date = today + dt.timedelta(days=int(command in ('/tomorrow', 'Завтра')))
        api(token, 'sendMessage', chat_id=chat_id, text=format_day(date), reply_markup=MENU)


def read(name, default=None):
    path = ROOT / name
    return json.loads(path.read_text()) if path.exists() else default


def save(name, data):
    path = ROOT / name
    temp = path.with_suffix('.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
    temp.replace(path)
    path.chmod(0o600)


class TelegramError(Exception):
    pass


def api(token, method, **params):
    request = urllib.request.Request(
        f'https://api.telegram.org/bot{token}/{method}',
        data=json.dumps(params).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        # Не печатаем URL запроса: он содержит токен.
        raise TelegramError(f'Telegram HTTP {error.code}') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise TelegramError('Не удалось подключиться к Telegram') from None
    if not result.get('ok'):
        raise TelegramError('Telegram отклонил запрос')
    return result['result']


def format_day(date):
    data = read('schedule.json')
    header = f'ИВТ-242 · {DAYS[date.weekday()]}, {date:%d.%m.%Y}'
    monday = date - dt.timedelta(days=date.weekday())
    key = monday.strftime('%d.%m')
    if date.year != data['year'] or key not in data['weeks']:
        return header + '\n\nВ загруженном файле нет расписания на эту неделю. Нужен новый файл.'
    parity = data['weeks'][key]
    lessons = data['days'][parity].get(str(date.weekday()), [])
    parts = [header, 'Чётная неделя' if parity == 'even' else 'Нечётная неделя']
    if not lessons:
        parts.append('По загруженному расписанию пар нет.')
    for lesson in lessons:
        number = lesson['number']
        clock = TIMES[number - 1] if number <= len(TIMES) else 'время не указано'
        parts.append(f"{number}-я пара · {clock}\n{lesson['subject']} ({lesson['kind']})\n{lesson['teacher']}\n{lesson['room']}")
        if lesson.get('note'):
            parts.append('Примечание из файла: ' + lesson['note'])
    return '\n\n'.join(parts)


def due(now, state):
    return (now.weekday() < 5 and (now.hour, now.minute) >= (7, 30)
            and state.get('sent') != now.date().isoformat())


def setup():
    pending = read('config.json', {})
    token = pending.get('token') or getpass.getpass('Вставь токен BotFather (ввод скрыт): ').strip()
    me = api(token, 'getMe')
    code = pending.get('pair_code') or secrets.token_hex(4)
    save('config.json', {'token': token, 'pair_code': code})
    print(f"Открой https://t.me/{me['username']} и отправь: /start {code}", flush=True)
    offset = 0
    while True:
        for update in api(token, 'getUpdates', offset=offset, timeout=20):
            offset = update['update_id'] + 1
            message = update.get('message', {})
            chat = message.get('chat', {})
            if chat.get('type') == 'private' and message.get('text', '').strip() == f'/start {code}':
                config = {'token': token, 'chat_id': chat['id']}
                save('config.json', config)
                save('state.json', {'offset': offset, 'sent': dt.datetime.now(MSK).date().isoformat()})
                api(token, 'sendMessage', chat_id=chat['id'], text='Бот подключён. Расписание: /today или /tomorrow. Уведомления — по будням в 07:30 по Москве, пока программа работает.\n\n' + format_day(dt.datetime.now(MSK).date()))
                print('Готово. Токен сохранён локально. Запускаю ежедневную отправку.', flush=True)
                return


def run():
    config = read('config.json')
    if not config:
        raise TelegramError('Сначала запусти: python3 bot.py --setup')
    state = read('state.json', {})
    print('Бот работает. Остановить: Ctrl+C.', flush=True)
    while True:
        try:
            now = dt.datetime.now(MSK)
            if due(now, state):
                api(config['token'], 'sendMessage', chat_id=config['chat_id'], text=format_day(now.date()), reply_markup=MENU)
                state['sent'] = now.date().isoformat()
                save('state.json', state)
            updates = api(config['token'], 'getUpdates', offset=state.get('offset', 0), timeout=20)
            for update in updates:
                handle_update(config, update, dt.datetime.now(MSK).date())
                state['offset'] = update['update_id'] + 1
                save('state.json', state)
        except TelegramError as error:
            print(str(error) + '. Повтор через 15 секунд.', flush=True)
            time.sleep(15)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', action='store_true')
    parser.add_argument('--preview', help='Дата YYYY-MM-DD без подключения к Telegram')
    args = parser.parse_args()
    try:
        if args.preview:
            print(format_day(dt.date.fromisoformat(args.preview)))
        else:
            if args.setup or not read('config.json', {}).get('chat_id'):
                setup()
            run()
    except TelegramError as error:
        print(error)
        raise SystemExit(1)
    except KeyboardInterrupt:
        print('\nБот остановлен.')
