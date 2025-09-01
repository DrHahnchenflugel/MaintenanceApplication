import os
from psycopg_pool import ConnectionPool

POOL = ConnectionPool(
    conninfo = os.environ["DATABASE_URL"],
    min_size = 1,
    max_size = 10,
    kwargs = {"options":"-c search_path=maintenance,pg_catalog"}
)

def query_one(sql:str, params:(str) = ()) -> str:
    with POOL.connection() as connection:
        with connection.cursor as cursor:
            cursor.execute(sql, params)
            single_row = cursor.fetchone()
            return single_row

def execute(sql:str, params:(str) = ()) -> None:
    with POOL.connection() as connection:
        with connection.cursor as cursor:
            cursor.execute(sql, params)