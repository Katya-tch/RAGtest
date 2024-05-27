import requests
import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command

from embeddings import select_from_db, get_embedding, select_simular_question, connect_to_db

router = Router()
with open("keys/tg.txt", 'r') as f:
    TG_KEY = f.read()
bot = Bot(token=TG_KEY, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2))
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

with open("keys/folder_id.txt", 'r') as f:
    FOLDER_ID = f.read()

url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
with open("keys/api_key.txt", 'r') as f:
    API_KEY = f.read()
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Api-Key {API_KEY}"
}

builder = InlineKeyboardBuilder()
builder.add(InlineKeyboardButton(text="Нормально", callback_data="good")).add(
    InlineKeyboardButton(text="Плохо...", callback_data="bad"))
user_data = {}


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


@router.message(Command("start"))
async def start_handler(msg: Message):
    await msg.answer("Привет! Я помогу тебе разобраться в устройстве ТюмГУ! Просто отправь вопрос")


@dp.callback_query(F.data == 'good')
async def process_callback_buttonGood(callback: types.CallbackQuery):
    user_value = user_data.get(callback.from_user.id, 0)

    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO cash (question, anwser, embedding, mark, doc) VALUES (%s, %s, %s, %s, %s);",
                (user_value[0], user_value[1], user_value[2], 1, user_value[3]))
    conn.commit()
    cur.close()
    await callback.message.answer('Спасибо за отзыв\! Можете задать следующий вопрос')


@dp.callback_query(F.data == 'bad')
async def process_callback_buttonBad(callback: types.CallbackQuery):
    user_value = user_data.get(callback.from_user.id, 0)

    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO cash (question, anwser, embedding, mark, doc) VALUES (%s, %s, %s, %s, %s);",
                (user_value[0], user_value[1], user_value[2], 0, user_value[3]))
    conn.commit()
    cur.close()
    await callback.message.answer('Спасибо за отзыв, мы учтем ваше мнение\! Можете задать следующий вопрос')


@router.message()
async def message_handler(msg: Message):
    msg_wait = await msg.answer(r"Обработка запроса\.\.\.")
    ecr = ['.', ',', "'", '"', '-', '(', ')', "@", '&', "!", '?']
    user_input = msg.text
    query_embedding = get_embedding(user_input, text_type="query")
    cash = select_simular_question(query_embedding)
    prompt = {
        "modelUri": "gpt://" + FOLDER_ID + "/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0,  # 0.6 по умолчанию
            "maxTokens": "2000"  # 2000 по умолчанию
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты ассистент в деканате ТюмГУ и помогаешь студентам разобраться в устройстве университета. "
                        "Отвечать на вопрос в тегах question нужно только на основе "
                        "предоставленного документа в тегах info. Отвечай на вопросы очень кратко."
            }
        ]
    }
    if cash:
        cash = cash.split('можно сделать вывод, что ')[-1]
        link = cash.split('###')[2]
        if link == "None":
            link = "мы обязательно добавим сюда ссылку\.\.\."
        cash = cash.split('###')[
                   0] + f"\n\n_Ответ получен на основе запросов других пользователей: {cash.split('###')[1]}_ На основании документа\: " + link
        cash = cash.replace("Согласно предоставленному документу, ", "")
        cash = cash.replace("Согласно информации в предоставленном документе, ", "")
        for i in ecr:
            cash = cash.replace(i, rf"\{i}")
        cash = cash.replace(r"\\", rf"\{''}").replace("**", "*").replace("*", "__")
        print(cash)
        await msg_wait.delete()
        await msg.answer(cash)
    else:
        i = 1
        result_final = ""
        s_final = ""
        stop_list = ["простите", "к сожалению", "извините", "прошу прощения", "не указан", "невозможно точно",
                     "нельзя точно"]
        while i <= 3:
            s = select_from_db(query_embedding, i)
            print(s.split(".txt")[0])  # название дока, который передается вместе с вопросом
            prompt["messages"] += [{"role": "user",
                                    "text": '[info]' + s + '[/info][question]' + user_input + '[/question]'}]

            response = requests.post(url, headers=headers, json=prompt)
            result = response.json()["result"]["alternatives"][0]["message"]["text"]

            # перебор всех фраз
            f = 0
            for j in stop_list:
                if j in result.lower():
                    f = 1
                    break
            if f:
                i += 1
                prompt["messages"] = prompt["messages"][:-1]
                if result_final == "":
                    result_final = result
                    s_final = s.split(".")[0]
            else:
                i = 4
                result_final = result
                s_final = s.split(".")[0]
                break

        result_final = result_final.split('можно сделать вывод, что ')[-1]
        result_final = result_final.replace("Согласно предоставленному документу, ", "")
        result_final = result_final.replace("Согласно информации в предоставленном документе, ", "")
        result_final = result_final.capitalize()
        for i in ecr:
            result_final = result_final.replace(i, rf"\{i}")
        result_final = result_final.replace(r"\\", rf"\{''}")
        result_final = result_final.replace(r"\\", rf"\{''}").replace("**", "*").replace("*", "__")
        await msg_wait.delete()
        print(result_final)
        link = "https\:\/\/github\.com\/Katya\-tch\/RAGtest\/blob\/main\/texts\/" + s_final + "\.pdf"
        resres = result_final + "\n\n_Ответ создан с использованием ИИ в режиме реального времени_ На основании документа\: " + link

        print(resres)
        await msg.answer(resres)

        await msg.answer(
            "Пожалуйста, оцените ответ бота\. Если Вы этого не сделаете, то ответ Бота будет утерян раз и навсегда\(\(",
            reply_markup=builder.as_markup())
        user_data[msg.from_user.id] = [user_input, result_final, query_embedding, link]


logging.basicConfig(level=logging.INFO)
asyncio.run(main())
