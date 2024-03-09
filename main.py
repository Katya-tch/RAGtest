from langchain.chat_models.gigachat import GigaChat
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from embeddings import select_from_db, get_embedding, select_simular_question, connect_to_db

with open("keys/credentials.txt", 'r') as f:
    credentials = f.read()
chat = GigaChat(
    credentials=credentials,
    verify_ssl_certs=False)
messages = [SystemMessage(
    content='Ты отвечаешь на вопросы по мультсериалу "Смешарики". '
            'Отвечать на вопрос в тегах question нужно только на основе'
            ' предоставленного документа в тегах info. Если в документе '
            'ответа на вопрос нет, напиши "Данной информации нет в базе.". '
            'Если вопрос не относится к Смешарикам, напиши "Я не специалист в этой теме.".')]
last_question = ""
while True:
    user_input = input("User: ")

    query_embedding = get_embedding(user_input, text_type="query")
    cash = select_simular_question(query_embedding)
    if cash:
        print("Base:", cash)
    else:
        i = 1
        ans = ""
        while i <= 3:
            s = select_from_db(query_embedding, i)
            # print(s)
            messages.append(HumanMessage(content='[info]' + s + '[/info][question]' + user_input +
                                                 '[/question]'))
            res = chat.invoke(input=messages)
            messages.append(res)
            # Ответ модели
            ans = res.content
            if "Данной информации нет в базе." in res.content:
                i += 1
            else:
                i = 4
                break

        print("Bot: ", ans)

        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO cash (question, anwser, embedding) VALUES (%s, %s, %s);",
                    (user_input, ans, query_embedding))
        conn.commit()
        cur.close()
    last_question = user_input
