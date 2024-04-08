import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from aiogram import types, F, Router
from aiogram.types import Message
from aiogram.filters import Command

import requests
from embeddings import select_from_db, get_embedding, select_simular_question, connect_to_db

router = Router()
with open("keys/folder_id.txt", 'r') as f:
    FOLDER_ID = f.read()

url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
with open("keys/api_key.txt", 'r') as f:
    API_KEY = f.read()
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Api-Key {API_KEY}"
}


@router.message(Command("start"))
async def start_handler(msg: Message):
    await msg.answer("Привет! Я помогу тебе разобраться в устройстве ТюмГУ! Просто отправь вопрос")


@router.message()
async def message_handler(msg: Message):
    user_input = msg.text
    query_embedding = get_embedding(user_input, text_type="query")
    cash = select_simular_question(query_embedding)
    prompt = {
        "modelUri": "gpt://" + FOLDER_ID + "/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0,  # 0.6 по умолчанию
            "maxTokens": "2000"  # 2000 было по умолчанию
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
        await msg.answer((cash + " (Base)").replace("**", "_"))
        # prompt["messages"] += [{"role": "user",
        #                         "text": '[question]' + user_input + '[/question]'}]
        # prompt["messages"] += [{"role": "assistant", "text": cash}]
    else:
        i = 1
        result = ""
        result_final = ""
        stop_list = ["простите", "к сожалению", "извините", "прошу прощения", "не указан", "невозможно точно",
                     "нельзя точно"]
        # stop_list = []
        while i <= 3:
            s = select_from_db(query_embedding, i)
            print(s.split(".txt")[0])  # название дока, который передается вместе с вопросом
            prompt["messages"] += [{"role": "user",
                                    "text": '[info]' + s + '[/info][question]' + user_input + '[/question]'}]

            response = requests.post(url, headers=headers, json=prompt)
            result = response.json()["result"]["alternatives"][0]["message"]["text"]
            # print(response.json()["result"]["alternatives"][0]["status"])
            result += f" ({response.json()['result']['usage']['totalTokens']})"
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
            else:
                i = 4
                result_final = result
                break

        await msg.answer((result_final + " (Bot)").replace("**", "_"))
        # prompt["messages"] += [{"role": "assistant", "text": result_final}]
        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO cash (question, anwser, embedding) VALUES (%s, %s, %s);",
                    (user_input, result_final, query_embedding))
        conn.commit()
        cur.close()
    # await msg.answer(f"Твой ID: {msg.from_user.id}")


async def main():
    bot = Bot(token="6937003260:AAHGuzLIbFKv8FeptGgckUdP5X7aS2JRpOE", parse_mode=ParseMode.MARKDOWN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


logging.basicConfig(level=logging.INFO)
asyncio.run(main())
