import datetime as dt
import unittest
from unittest.mock import patch
import bot


class ScheduleTests(unittest.TestCase):
    def test_calendar_year_boundary(self):
        rows = bot.calendar_week(dt.date(2026, 12, 31))['inline_keyboard']
        self.assertEqual(rows[0][0]['callback_data'], 'day:2026-12-28')
        self.assertEqual(rows[6][0]['callback_data'], 'day:2027-01-03')
        self.assertEqual(rows[7][1]['callback_data'], 'week:2027-01-04')

    @patch('bot.api')
    def test_selected_day(self, api):
        update = {'callback_query': {'id': 'example', 'data': 'day:2026-11-05',
                                     'message': {'chat': {'id': 1}, 'message_id': 3}}}
        bot.handle_update({'token': 'dummy', 'chat_id': 1}, update, dt.date(2026, 10, 29))
        self.assertIn('05.11.2026', api.call_args.kwargs['text'])
        self.assertIn('Чётная неделя', api.call_args.kwargs['text'])

    @patch('bot.api')
    def test_foreign_chat(self, api):
        bot.handle_update({'token': 'dummy', 'chat_id': 1},
                          {'message': {'chat': {'id': 2}, 'text': '/days'}}, dt.date(2026, 10, 29))
        api.assert_not_called()

    @patch('bot.api')
    def test_invalid_callback(self, api):
        bot.handle_update({'token': 'dummy', 'chat_id': 1},
                          {'callback_query': {'id': 'bad', 'data': 'day:invalid', 'message': {'chat': {'id': 1}}}},
                          dt.date(2026, 10, 29))
        self.assertEqual(api.call_args.args[1], 'answerCallbackQuery')

    def test_odd_thursday(self):
        text = bot.format_day(dt.date(2026, 10, 29))
        self.assertIn('Нечётная неделя', text)
        self.assertIn('1-я пара · 08:00–09:30', text)
        self.assertIn('Схемотехника (ЛК)', text)

    def test_even_thursday(self):
        text = bot.format_day(dt.date(2026, 11, 5))
        self.assertIn('Чётная неделя', text)
        self.assertNotIn('1-я пара', text)
        self.assertIn('2-я пара · 09:50–11:20', text)

    def test_weekend(self):
        self.assertIn('пар нет', bot.format_day(dt.date(2026, 10, 31)))

    def test_outside_source(self):
        self.assertIn('Нужен новый файл', bot.format_day(dt.date(2027, 10, 29)))
        self.assertIn('Нужен новый файл', bot.format_day(dt.date(2026, 12, 28)))

    def test_delivery(self):
        for stamp, expected in [('2026-10-30T07:29', False), ('2026-10-30T07:30', True),
                                ('2026-10-31T07:30', False), ('2026-11-01T07:30', False)]:
            now = dt.datetime.fromisoformat(stamp).replace(tzinfo=bot.MSK)
            self.assertEqual(bot.due(now, {}), expected)
        now = dt.datetime(2026, 10, 30, 7, 30, tzinfo=bot.MSK)
        self.assertFalse(bot.due(now, {'sent': '2026-10-30'}))


if __name__ == '__main__':
    unittest.main()
