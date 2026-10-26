import psycopg2

connection = psycopg2.connect(
    host="localhost",
    port=5432,
    database="marketplace",
    user="marketplace",
    password="password"
)

print("Connected to PostgreSQL!")