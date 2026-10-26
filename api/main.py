from fastapi import FastAPI
from api.db import connection

app = FastAPI()


@app.get("/")
def home():
    return {"message": "AI Marketplace is alive!"}


@app.get("/requests")
def get_requests():
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM requests;")

    requests = cursor.fetchall()

    cursor.close()

    return {"requests": requests}