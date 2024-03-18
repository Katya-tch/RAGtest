import requests
from embeddings import select_from_db, get_embedding, select_simular_question, connect_to_db

with open("keys/folder_id.txt", 'r') as f:
    FOLDER_ID = f.read()
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

url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
with open("keys/api_key.txt", 'r') as f:
    API_KEY = f.read()
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Api-Key {API_KEY}"
}

while True:
    if len(prompt["messages"]) >= 3:
        prompt["messages"][-2]["text"] = prompt["messages"][-2]["text"].split("[question]")[-1].replace("[/question]", '')
        prompt["messages"] = [
            {
                "role": "system",
                "text": "Ты ассистент в деканате ТюмГУ и помогаешь студентам разобраться в устройстве университета. "
                        "Отвечать на вопрос в тегах question нужно ТОЛЬКО на основе "
                        "предоставленного документа в тегах info. Отвечай на вопросы очень кратко."
            }, prompt["messages"][-2], prompt["messages"][-1]
        ]
    # print(prompt["messages"])

    user_input = input("User: ")
    query_embedding = get_embedding(user_input, text_type="query")
    cash = select_simular_question(query_embedding)
    if cash:
        print("Base:", cash)
        prompt["messages"] += [{"role": "user",
                               "text": '[question]' + user_input + '[/question]'}]
        prompt["messages"] += [{"role": "assistant", "text": cash}]
    else:
        i = 1
        result = ""
        while i <= 3:
            s = select_from_db(query_embedding, i)
            print(s.split(".txt")[0])  # название дока, который передается вместе с вопросом
            prompt["messages"] += [{"role": "user",
                                   "text": '[info]' + s + '[/info][question]' + user_input + '[/question]'}]

            response = requests.post(url, headers=headers, json=prompt)
            result = response.json()["result"]["alternatives"][0]["message"]["text"]
            print(response.json()["result"]["alternatives"][0]["status"])
            result += f" ({response.json()['result']['usage']['totalTokens']})"
            # написать функцию для перебора всех фраз
            if "к сожалению" in result.lower() or "простите" in result.lower() or "нет информации" in result.lower():
                i += 1
                prompt["messages"] = prompt["messages"][:-1]
            else:
                i = 4
                break

        print("Bot: ", result, "\n")
        prompt["messages"] += [{"role": "assistant", "text": result}]
        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO cash (question, anwser, embedding) VALUES (%s, %s, %s);",
                    (user_input, result, query_embedding))
        conn.commit()
        cur.close()

