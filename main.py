from langchain.chat_models.gigachat import GigaChat
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from embeddings import select_from_db, get_embedding, select_simular_question, connect_to_db

chat = GigaChat(
    credentials='<MAIN.PY(static to gigachat)>',
    verify_ssl_certs=False)
messages = [SystemMessage(
    content='Ты виртуальный помощник для поиска информации в тексте. Отвечать на вопрос нужно только на основе'
            ' предоставленной в нем информации. Если вопрос не относится к теме "Смешариков", не отвечай на него.')]
last_question = ""
while True:
    user_input = input("User: ")

    query_embedding = get_embedding(user_input, text_type="query")
    cash = select_simular_question(query_embedding)
    if cash:
        print("Base:", cash)
    else:
        s = select_from_db(query_embedding) + " " + last_question
        messages.append(HumanMessage(content=' Прочитай текст в '
             'тегах info и ответь на вопрос в тегах question не более 20 словами. Для ответа используй информацию только из '
             'предоставленного текста в тегах question. Если ответа нет в тексте, не бери его из других источников. '
             '[info]' + s + '[/info][question]' + user_input +
             '[/question]'))
        res = chat.invoke(input=messages)
        messages.append(res)
        # Ответ модели
        print("Bot: ", res.content)

        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO cash (question, anwser, embedding) VALUES (%s, %s, %s);", (user_input, res.content, query_embedding))
        conn.commit()
        cur.close()
    last_question = user_input
