import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.executor import start_webhook
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.webhook import get_new_configured_app
# from aiogram.utils import context
import aiohttp
from aiohttp import web
import asyncio

import os
from selenium import webdriver
from bs4 import BeautifulSoup
from threading import Thread
import schedule
import time
import datetime
from urllib.parse import urljoin
from flask import Flask, request

BOT_TOKEN = 'token'
HEROKU_APP_NAME = os.getenv('aiomybot')

TOKEN = BOT_TOKEN  # Press "Reveal Config Vars" in settings tab on Heroku and set TOKEN variable
PROJECT_NAME = HEROKU_APP_NAME  # Set it as you've set TOKEN env var

WEBHOOK_HOST = f'https://{PROJECT_NAME}.herokuapp.com/'  # Enter here your link from Heroku project settings
WEBHOOK_URL_PATH = '/webhook/' + TOKEN
WEBHOOK_URL = urljoin(WEBHOOK_HOST, WEBHOOK_URL_PATH)
# # webhook settings
# WEBHOOK_HOST = f'https://{HEROKU_APP_NAME}.herokuapp.com'
# WEBHOOK_PATH = f'/webhook/{BOT_TOKEN}'
# WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'
#
# # webserver settings
# WEBAPP_HOST = '0.0.0.0'
# WEBAPP_PORT = int(os.getenv('PORT'))

keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add('Запустить бота')

keyboard_main = types.ReplyKeyboardMarkup(resize_keyboard=True)
keyboard_main.add('Подписаться на игры')
keyboard_main.add('Отписаться')
keyboard_main.add('Обновить', 'Количество')

adm_keyb = types.ReplyKeyboardMarkup(resize_keyboard=True)
adm_keyb.add('Ввести прогноз')
adm_keyb.add('Очистить')

users_id = []
pre_match = {}
live_game = {}
uved_user = []
prognoz = ''

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
# server = Flask(__name__)
dp.middleware.setup(LoggingMiddleware())


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await message.answer('Запусти бота', reply_markup=keyboard)



class Form(StatesGroup):
    pprognoz = State()  # Will be represented in storage as 'Form:name'
    clear_all = State()


@dp.message_handler()
async def get_text_messages(message: types.Message):
    if message.text == "/help":
        await message.answer("Введите /start")
        if message.from_user.id == 79145277:
            await message.answer("Ввести прогноз", reply_markup=adm_keyb)
    elif message.text.lower() == 'запустить бота':
        await message.answer("Выводить игры", reply_markup=keyboard_main)
    elif message.text.lower() == 'подписаться на игры':
        if not message.from_user.id in users_id:
            users_id.append(message.from_user.id)
            await message.answer("Вы подписаны")
        else:
            await message.answer("Вы уже подписаны")
    elif message.text.lower() == 'отписаться':
        if message.from_user.id in users_id:
            users_id.remove(message.from_user.id)
            await message.answer("Вы отписаны")
        else:
            await message.answer("Вы уже отписаны")
        # myScore_parse()
    elif message.text.lower() == 'обновить':
        for i in users_id:
            await message.answer(i)
        await message.answer(str(len(users_id)))
        # myScore_parse()
        # bot.send_message(message.from_user.id, "Игры обновились")

    elif message.text.lower() == 'количество':
        await message.answer(str(len(pre_match)) + ' - количество возможных игр')
        for i in pre_match:
            text_msg = pre_match[i]['time'] + ' ' + pre_match[i]['first_team'] + ' ' + pre_match[i][
                'second_team'] + ' ' + pre_match[i]['score'] + ' ' + pre_match[i]['kef_x1'] + ' ' + pre_match[i][
                           'kef_x2'] + ' ' + pre_match[i]['url']
            await message.answer(text_msg)
            # bot.send_message(message.from_user.id, pre_match[id]['url'])
    elif message.text.lower() == 'ввести прогноз':
        if message.from_user.id == 79145277:
            await Form.pprognoz.set()
    elif message.text.lower() == 'очистить':
        if message.from_user.id == 79145277:
            await Form.clear_all.set()
    else:
        await message.answer("Я тебя не понимаю. Напиши /help.")


@dp.message_handler(state=Form.pprognoz)
async def process_name(message: types.Message, state: FSMContext):
    prognoz = message.text
    for i in users_id:
        await bot.send_message(i, prognoz)
    await state.finish()

@dp.message_handler(state=Form.clear_all)
async def clear_parse(message: types.Message, state: FSMContext):
    pre_match.clear()
    live_game.clear()
    users_id.clear()
    uved_user.clear()
    await message.answer('Удалено')
    await state.finish()

async def myScore_parse_live():
    myscore = 'https://www.flashscore.ru/volleyball/'
    # # tennis = 'https://www.flashscore.ru/tennis/'
    # site = ['https://www.flashscore.ru/volleyball/', 'https://www.flashscore.ru/tennis/']
    # for myscore in site:
    game = 'volleyball'
    CHROMEDRIVER_PATH = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
    GOOGLE_CHROME_BIN = os.environ.get('GOOGLE_CHROME_BIN', '/usr/bin/google-chrome')
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.binary_location = GOOGLE_CHROME_BIN
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.headless = True
    #
    driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, options=chrome_options)
    driver.implicitly_wait(10)
    driver.get(myscore)

    # driver = webdriver.Chrome("C:\Selenium\Chrome\chromedriver.exe", options=chrome_options)
    # driver.implicitly_wait(10)
    # driver.get(myscore)

    elements = driver.find_elements_by_css_selector("div.tabs__tab")
    await asyncio.sleep(5)
    try:
        elements[3].click()
        await asyncio.sleep(5)
        container = driver.find_element_by_css_selector("div[id=live-table]").get_attribute("innerHTML")
        await track_match(container, game)
        await live_match(container, game)
        driver.close()
    except:
        driver.close()
    driver.quit()
    # get_bet()


async def tennis_game():
    tennis = 'https://www.flashscore.ru/tennis/'
    game = 'tennis'

    CHROMEDRIVER_PATH = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
    GOOGLE_CHROME_BIN = os.environ.get('GOOGLE_CHROME_BIN', '/usr/bin/google-chrome')
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.binary_location = GOOGLE_CHROME_BIN
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.headless = True
    #
    driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, options=chrome_options)
    driver.implicitly_wait(10)
    driver.get(tennis)

    # driver = webdriver.Chrome("C:\Selenium\Chrome\chromedriver.exe", options=chrome_options)
    # driver.implicitly_wait(10)
    # driver.get(tennis)

    elements = driver.find_elements_by_css_selector("div.tabs__tab")
    await asyncio.sleep(5)
    try:
        elements[3].click()
        await asyncio.sleep(5)
        container = driver.find_element_by_css_selector("div[id=live-table]").get_attribute("innerHTML")
        await track_match(container, game)
        await live_match(container, game)
        driver.close()
    except:
        driver.close()
    driver.quit()


async def track_match(container, game):
    soup = BeautifulSoup(container, 'html.parser')
    matches = soup.select(".event__match.event__match--scheduled.event__match--oneLine")
    # pre_match = {}
    for match in matches:
        time_match = match.select_one('div.event__time')
        p1 = match.select_one('div.event__participant--home')
        p2 = match.select_one('div.event__participant--away')
        score = match.select_one('div.event__scores')
        x1 = match.select_one('div.event__odd--odd1')
        x2 = match.select_one('div.event__odd--odd2')
        id_match = match["id"].split("_")[-1]
        url = 'https://www.flashscore.ru/match/{}/#match-summary'.format(id_match)
        # print(time_match.text, p1.text, p2.text, score.text, x1.text, x2.text, url)
        text_msg = time_match.text + ' ' + p1.text + ' ' + p2.text + ' ' + score.text + ' ' + x1.text + ' ' + x2.text + ' ' + url
        # for id in users_id:
        #     bot.send_message(id, text_msg)
        if time_match.text.find('TKP') == -1:
            if (x1.text != None or x2.text != None) and (x1.text != '-' and x2.text != '-'):
                kef_one = float(x1.text)
                kef_two = float(x2.text)
                if 1.1 <= kef_one <= 1.4 or 1.1 <= kef_two <= 1.4:
                    if not (id_match in pre_match):
                        pre_match[id_match] = {'time': time_match.text, 'first_team': p1.text, 'second_team': p2.text,
                                               'score': score.text, 'kef_x1': x1.text, 'kef_x2': x2.text, 'url': url,
                                               'game': game}
                    else:
                        if not (1.1 <= kef_one <= 1.4 and 1.1 <= float(pre_match[id_match]['kef_x1']) <= 1.4) and not (
                                1.1 <= kef_two <= 1.4 and 1.1 <= float(pre_match[id_match]['kef_x2']) <= 1.4):
                            pre_match[id_match]['dogovor'] = True
                        # for id in users_id:
                        #     bot.send_message(id, text_msg)
                        #     bot.send_message(id, 'Возможная игра')
                if id_match in pre_match:
                    if not (1.1 <= kef_one <= 1.4 and 1.1 <= float(pre_match[id_match]['kef_x1']) <= 1.4) and not (
                            1.1 <= kef_two <= 1.4 and 1.1 <= float(pre_match[id_match]['kef_x2']) <= 1.4):
                        pre_match[id_match]['dogovor'] = True
        # for id in users_id:
        #     bot.send_message(id, len(pre_match))
    # print("=======Игры========")
    # print(pre_match)


async def live_match(container, game):
    soup = BeautifulSoup(container, 'html.parser')
    matches = soup.select(".event__match.event__match--live.event__match--oneLine")
    for match in matches:
        time_match = match.select_one('div.event__stage')
        p1 = match.select_one('div.event__participant--home')
        p2 = match.select_one('div.event__participant--away')
        score = match.select_one('div.event__scores')
        x1 = match.select_one('div.event__odd--odd1')
        x2 = match.select_one('div.event__odd--odd2')
        id_match = match["id"].split("_")[-1]
        url = 'https://www.flashscore.ru/match/{}/#match-summary'.format(id_match)
        # print(time_match.text, p1.text, p2.text, score.text, x1.text, x2.text, url)
        # text_msg = time_match.text + ' ' + p1.text + ' ' + p2.text + ' ' + score.text + ' ' + x1.text + ' ' + x2.text + ' ' + url
        text_msg = time_match.text + '\n' + p1.text + ' - ' + x1.text + '\n' + p2.text + ' - ' + x2.text + '\n' + score.text + '\n' + url

        if id_match in pre_match:
            text_msg = game + '\n' + text_msg
            if 'dogovor' in pre_match[id_match].keys():
                if pre_match[id_match]['dogovor'] == True:
                    text_msg = text_msg + ' Dogovor'

            if not id_match in uved_user:
                if score.text == '0 - 0' and time_match.text == '1-й сет':
                    # if 1.1 <= float(x1.text) <= 1.5 or 1.1 <= float(x2.text) <= 1.5:
                    for id_us in users_id:
                        # bot.send_message(id_us, text_msg)
                        await bot.send_message(id_us, 'Игра началась' + '\n' + text_msg)
                        uved_user.append(id_match)

            if not id_match in live_game:
                if id_match in uved_user:
                    # live_game[id_match] = {'time': time_match.text, 'first_team': p1.text, 'second_team': p2.text, 'score': score.text, 'kef_x1': x1.text, 'kef_x2': x2.text, 'url': url}
                    if 1.1 <= float(pre_match[id_match]['kef_x1']) <= 1.4:
                        if score.text == '0 - 1':
                            # for id_us in users_id:
                            #     text_msg = text_msg +'\n' + p1.text + ' выиграет 2-й сет, ставить когда будет ввести разницей в 2 очка'
                            #     bot.send_message(id_us, text_msg)
                            # bot.send_message(id_us, p1.text + ' выиграет 2-й сет, ставить когда будет ввести разницей в 2 очка')
                            live_game[id_match] = {'time': time_match.text, 'first_team': p1.text,
                                                   'second_team': p2.text,
                                                   'score': score.text, 'kef_x1': x1.text, 'kef_x2': x2.text,
                                                   'url': url}
                            if game == 'volleyball':
                                for id_us in users_id:
                                    text_msg = text_msg + '\n' + p1.text + ' выиграет 2-й сет ИЛИ ТОТАЛ 44.5Б - ИТ1 19.5Б и ИТ2 19.5Б'
                                    await bot.send_message(id_us, text_msg)
                            elif game == 'tennis':
                                for id_us in users_id:
                                    text_msg = text_msg + '\n' + p1.text + ' выиграет 2-й сет'
                                    await bot.send_message(id_us, text_msg)
                    if 1.1 <= float(pre_match[id_match]['kef_x2']) <= 1.4:
                        if score.text == '1 - 0':
                            # for id_us in users_id:
                            #     text_msg = text_msg + '\n' + p2.text + ' выиграет 2-й сет, ставить когда будет ввести разницей в 2 очка'
                            #     bot.send_message(id_us, text_msg)
                            # bot.send_message(id_us, p2.text + ' выиграет 2-й сет, ставить когда будет ввести разницей в 2 очка')
                            live_game[id_match] = {'time': time_match.text, 'first_team': p1.text,
                                                   'second_team': p2.text,
                                                   'score': score.text, 'kef_x1': x1.text, 'kef_x2': x2.text,
                                                   'url': url}
                            if game == 'volleyball':
                                for id_us in users_id:
                                    text_msg = text_msg + '\n' + p2.text + ' выиграет 2-й сет ИЛИ ТОТАЛ 44.5Б - ИТ1 19.5Б и ИТ2 19.5Б'
                                    await bot.send_message(id_us, text_msg)
                            elif game == 'tennis':
                                for id_us in users_id:
                                    text_msg = text_msg + '\n' + p2.text + ' выиграет 2-й сет'
                                    await bot.send_message(id_us, text_msg)
    # print('======live=====================')
    # print(live_game)

async def run_myscore():
    await schedule.every().day.at("05:30").do(clear_parse)
    while True:
        await schedule.run_pending()


async def run_live_score():
    while True:
        # myScore_parse()
        print('Hello')
        await myScore_parse_live()
        await asyncio.sleep(5)
        await tennis_game()
        await asyncio.sleep(5)
        print('end')


async def on_startup(app):
    """Simple hook for aiohttp application which manages webhook"""
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)


if __name__ == '__main__':
    # Create aiohttp.web.Application with configured route for webhook path
    # app = get_new_configured_app(dispatcher=dp, path=WEBHOOK_URL_PATH)
    # app.on_startup.append(on_startup)
    # # dp.loop.set_task_factory(context.task_factory)
    # web.run_app(app, host='0.0.0.0', port=os.getenv('PORT'))
    loop = asyncio.get_event_loop()
    loop.create_task(run_live_score())
    executor.start_polling(dp, skip_updates=True)
