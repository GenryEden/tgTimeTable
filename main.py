import telebot
from telebot import types
import json
import config
import datetime
import time

bot = telebot.TeleBot(config.token)
updatingClocks = {}
updatingLessons = {}
week = ['Понедельник',
        'Вторник',
        'Среда',
        'Четверг',
        'Пятница',
        'Суббота',
        'Воскресенье']


def readDB():
    dataBase = {}
    try:
        file = open(config.fileName)
    except FileNotFoundError:
        file = open(config.fileName, 'w')
        file.write(json.dumps(dataBase))
        file.close()
    else:
        dataBase = json.loads(file.read())
        file.close()
    return dataBase


def writeDB(dataBase):
    with open(config.fileName, 'w') as file:
        file.write(json.dumps(dataBase, indent=4, sort_keys=True))
        file.close()


dataBase = readDB()


@bot.message_handler(commands=['start', 'help'])
def startMessage(message):
    bot.send_message(message.chat.id, config.helloText)


@bot.message_handler(commands=['calls'])
def callsCommand(message):
    if dataBase.get(str(message.chat.id)) is None:
        dataBase[str(message.chat.id)] = {}
    updatingClocks[str(message.chat.id)] = {}
    markup = types.ReplyKeyboardMarkup()
    markup.row(*list(map(str, range(1, 10))))

    bot.send_message(
        message.chat.id,
        text='Время какого урока ты хочешь изменить?',
        reply_markup=markup
    )
    bot.register_next_step_handler(message, chooseModeForCall)


def chooseModeForCall(message):
    try:
        assert (1 <= int(message.text) <= 9)
    except (ValueError, AssertionError):
        markup = types.ReplyKeyboardMarkup()
        markup.row(*list(map(str, range(1, 10))))

        bot.send_message(
            message.chat.id,
            text='Попробуй еще раз',
            reply_markup=markup
        )
        bot.register_next_step_handler(message, chooseModeForCall)
        return
    userUpdatingClocks = updatingClocks[str(message.chat.id)]
    userUpdatingClocks['lesson'] = int(message.text)

    markup = types.ReplyKeyboardMarkup()
    markup.row('Начало', 'Конец')
    bot.send_message(
        message.chat.id,
        'Что ты хочешь изменить - начало урока или его конец?',
        reply_markup=markup
    )
    bot.register_next_step_handler(message, chooseHour)


def chooseHour(message):
    text = message.text.lower()
    userUpdatingClocks = updatingClocks[str(message.chat.id)]
    if text == 'начало':
        userUpdatingClocks['mode'] = 's'
        ans = 'Во сколько часов начинается урок?'
    elif text == 'конец':
        userUpdatingClocks['mode'] = 'e'
        ans = 'Во сколько часов заканчивается урок?'
    else:
        markup = types.ReplyKeyboardMarkup()
        markup.row('Начало', 'Конец')
        bot.send_message(
            message.chat.id,
            'Попробуй еще раз!',
            reply_markup=markup
        )
        bot.register_next_step_handler(message, chooseHour)
        return
    markup = types.ReplyKeyboardMarkup()
    for x in range(0, 24, 6):
        markup.row(*list(map(str, range(x, x+6))))
    bot.send_message(
        message.chat.id,
        ans,
        reply_markup=markup
    )
    bot.register_next_step_handler(message, chooseMinute)


def chooseMinute(message):
    try:
        assert (0 <= int(message.text) <= 23)
    except (ValueError, AssertionError):
        markup = types.ReplyKeyboardMarkup()
        for x in range(0, 24, 6):
            markup.row(*list(map(str, range(x, x+6))))
        bot.send_message(
            message.chat.id,
            'Попробуй еще раз!',
            reply_markup=markup
        )
        bot.register_next_step_handler(message, chooseMinute)
        return
    userUpdatingClocks = updatingClocks[str(message.chat.id)]
    userUpdatingClocks['hours'] = int(message.text)
    markup = types.ReplyKeyboardMarkup()
    for x in range(0, 45, 30):
        markup.row(*list(map(str, range(x, x+30, 5))))
    bot.send_message(
        message.chat.id,
        'А во сколько минут?',
        reply_markup=markup
    )
    bot.register_next_step_handler(message, updateClocks)


def updateClocks(message):
    try:
        assert (0 <= int(message.text) <= 59)
    except (ValueError, AssertionError):
        markup = types.ReplyKeyboardMarkup()
        for x in range(0, 45, 30):
            markup.row(*list(map(str, range(x, x+30, 5))))
        bot.send_message(
            message.chat.id,
            'Попробуй еще раз!',
            reply_markup=markup
        )
        bot.register_next_step_handler(message, updateClocks)
        return
    userUpdatingClocks = updatingClocks[str(message.chat.id)]
    userUpdatingClocks['minutes'] = int(message.text)

    dbUser = dataBase.get(str(message.chat.id))
    if dbUser is None:
        dataBase[str(message.chat.id)] = {'clocks': {}}
        dbUser = dataBase.get(str(message.chat.id))

    dbParse = dbUser.get('clocks')
    if dbParse is None:
        dbUser['clocks'] = {}
        dbParse = dbUser.get('clocks')

    # print(dataBase, dbParse, dbUser)
    if dbParse.get(str(userUpdatingClocks['lesson'])) is None:
        dbParse[str(userUpdatingClocks['lesson'])] = {}
    dbLesson = dbParse[str(userUpdatingClocks['lesson'])]
    dbLesson[userUpdatingClocks['mode']] = (
        str(userUpdatingClocks['hours']) + ":" +
        str(userUpdatingClocks['minutes'])
    )
    try:
        if dbLesson['s'] > dbLesson['e']:
            ans = (
                '''Начало урока не может быть позже конца,'''
                ''' я поменял их местами'''
            )
            dbLesson['s'], dbLesson['e'] = dbLesson['e'], dbLesson['s']
        else:
            ans = 'Принято!'
    except KeyError:
        ans = 'Принято!'
    markup = types.ReplyKeyboardRemove()
    writeDB(dataBase)
    bot.send_message(message.chat.id, ans, reply_markup=markup)
    # print(dataBase)

@bot.message_handler(commands=['lessons'])
def lessonsCommand(message):
    markup = types.ReplyKeyboardMarkup()
    markup.row(*week[:-2])
    markup.row(*week[-2:])
    updatingLessons[str(message.chat.id)] = {}
    bot.send_message(message.chat.id, 'Выбери день недели', reply_markup=markup)
    bot.register_next_step_handler(message, chooseLessonNumber)

def chooseLessonNumber(message):
    try:
        assert message.text.lower() in list(
                map(
                    lambda x: x.lower(),
                    week
                )
            )
    except (ValueError, AssertionError):
        markup = types.ReplyKeyboardMarkup()
        markup.row(*week[:-2])
        markup.row(*week[-2:])
        bot.send_message(
            message.chat.id,
            'Попробуй еще раз!',
            reply_markup=markup
        )
        bot.register_next_step_handler(message, chooseLessonNumber)
        return
    userUpdatingLesson = updatingLessons[str(message.chat.id)]
    userUpdatingLesson['day'] = list(
        map(
            lambda x: x.lower(),
            week
        )
    ).index(message.text.lower())

    markup = types.ReplyKeyboardMarkup()
    markup.row(*list(map(str, range(1,10))))
    bot.send_message(
        message.chat.id,
        'Выбери номер урока',
        reply_markup=markup
    )
    # print(userUpdatingLesson)
    bot.register_next_step_handler(message, getLessonName)

def getLessonName(message):
    try:
        assert (1 <= int(message.text) <= 9)
    except (ValueError, AssertionError):
        markup = types.ReplyKeyboardMarkup()
        markup.row(*list(map(str, range(1, 10))))

        bot.send_message(
            message.chat.id,
            text='Попробуй еще раз',
            reply_markup=markup
        )
        bot.register_next_step_handler(message, getLessonName)
        return
    userUpdatingLesson = updatingLessons[str(message.chat.id)]
    userUpdatingLesson['number'] = (message.text)

    markup = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,
        'Введи название урока',
        reply_markup=markup
    )
    bot.register_next_step_handler(message, updateLessons)

    pass

def updateLessons(message):
    userUpdatingLesson = updatingLessons[str(message.chat.id)]
    userUpdatingLesson['name'] = message.text
    # print(userUpdatingLesson)
    dbUser = dataBase.get(str(message.chat.id))
    if dbUser is None:
        dataBase[str(message.chat.id)] = {'lessons':{}}
        dbUser = dataBase.get(str(message.chat.id))
    if not 'lessons' in dbUser:
        dbUser['lessons'] = {}
    dbLessons = dbUser['lessons']
    if not str(userUpdatingLesson['day']) in dbLessons:
        dbLessons[str(userUpdatingLesson['day'])] = {}
    dbDay = dbLessons.get(str(userUpdatingLesson['day']))
    dbDay[str(userUpdatingLesson['number'])] = userUpdatingLesson['name']
    writeDB(dataBase)
    markup = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,
        text='Принято',
        reply_markup=markup
    )
    pass


@bot.message_handler(commands=['table'])
def getTable(message):
    dbUser = dataBase.get(str(message.chat.id))
    ans = 'Расписание звонков:\n'
    if not 'clocks' in dbUser:
        dbUser['clocks'] = {}
        writeDB(dataBase)

    for x in dbUser['clocks']:
        clock = dbUser['clocks'][x]
        ans += f'{x}. '
        if 's' in clock:
            ans += str(clock['s'])
        else:
            ans += '??'
        ans += '-'
        if 'e' in clock:
            ans += str(clock['e'])
        else:
            ans += '??'
        ans += '\n'
    bot.send_message(
        message.chat.id,
        ans
    )
    if not 'lessons' in dbUser:
        dbUser['lessons'] = {}
        writeDB(dataBase)

    for x in dbUser['lessons']:
        ans = week[int(x)] + '\n'
        for y in dbUser['lessons'][x]:
            lesson = dbUser['lessons'][x][y]
            ans += f'{y}. {lesson}'
            ans += '\n'
        bot.send_message(
            message.chat.id,
            ans
        )

@bot.message_handler(commands=['today'])
def getTodayTable(message):
    today = str(datetime.datetime.today().weekday())
    ans = ''
    dbUser = dataBase.get(str(message.chat.id))
    if not 'lessons' in dbUser:
        dbUser['lessons'] = {}
        writeDB(dataBase)
    if today in dbUser['lessons']:
        for y in dbUser['lessons'][today]:
            lesson = dbUser['lessons'][today][y]
            ans += f'{y}. {lesson}'
            ans += '\n'
    else:
        ans = 'На этот день нет уроков'
    bot.send_message(
        message.chat.id,
        ans
    )


@bot.message_handler(commands=['callstable'])
def getCallsTable(message):
    dbUser = dataBase.get(str(message.chat.id))
    ans = 'Расписание звонков:\n'
    if not 'clocks' in dbUser:
        dbUser['clocks'] = {}
        writeDB(dataBase)

    for x in dbUser['clocks']:
        clock = dbUser['clocks'][x]
        ans += f'{x}. '
        if 's' in clock:
            ans += str(clock['s'])
        else:
            ans += '??'
        ans += '-'
        if 'e' in clock:
            ans += str(clock['e'])
        else:
            ans += '??'
        ans += '\n'
    bot.send_message(
        message.chat.id,
        ans
    )
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(e)
        bot.stop_polling()
        time.sleep(5)
