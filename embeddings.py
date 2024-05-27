import requests

import numpy as np
from pgvector.psycopg2 import register_vector
import psycopg2


def get_embedding(text: str, text_type: str = "doc") -> np.array:
    with open("keys/folder_id.txt", 'r') as f:
        FOLDER_ID = f.read()
    # with open("keys/iam_token.txt", 'r') as f:
    #     IAM_TOKEN = f.read().replace("\n", "")
    with open("keys/api_key.txt", 'r') as f:
        API_KEY = f.read()

    doc_uri = f"emb://{FOLDER_ID}/text-search-doc/latest"
    query_uri = f"emb://{FOLDER_ID}/text-search-query/latest"

    embed_url = "https://llm.api.cloud.yandex.net:443/foundationModels/v1/textEmbedding"
    headers = {"Content-Type": "application/json", "Authorization": f"Api-Key {API_KEY}",
               "x-folder-id": f"{FOLDER_ID}"}

    query_data = {
        "modelUri": doc_uri if text_type == "doc" else query_uri,
        "text": text,
    }
    return np.array(
        requests.post(embed_url, json=query_data, headers=headers).json()["embedding"]
    )


def connect_to_db():
    with open("keys/base.txt", 'r') as f:
        password = f.read()
    conn = psycopg2.connect(
        host="localhost",
        database="textgpt",
        user="postgres",
        password=password)
    register_vector(conn)
    return conn


def select_from_db(query_vector, i):
    conn = connect_to_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT name, content, embedding <-> %s AS similarity
    FROM embeddings
    ORDER BY similarity ASC
    LIMIT %s;
    """, (query_vector, i))

    results = cur.fetchall()
    s = ""
    for row in results:
        s = str(row[0]) + str(row[1]) + "\n"

    cur.close()
    return s


def select_simular_question(query_vector):
    conn = connect_to_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT question, anwser, doc, embedding <-> %s AS similarity
        FROM cash
        WHERE mark=1
        ORDER BY similarity ASC
        LIMIT 1;
        """, (query_vector,))

    results = cur.fetchall()
    s = ""
    for row in results:
        if float(row[3]) < 0.4:
            s = str(row[1]) + "###" + str(row[0]) + "###" + str(row[2])
        else:
            s = None

    cur.close()
    return s
