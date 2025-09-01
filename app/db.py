import os
from psycopg_pool import ConnectionPool

POOL = ConnectionPool(
    conninfo = os.environ["DATABASE_URL"],
    min_size = 1,
    max_size = 10,
    kwargs = {"options":"-c search_path=maintenance,pg_catalog"}
)

def query_one(sql:str, params:(str) = ()) -> str|None:
    with POOL.connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            single_row = cursor.fetchone()
            return single_row

def query_all(sql:str, params:(str) = ()) -> str|None:
    with POOL.connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return rows

def execute(sql:str, params:(str) = ()) -> None:
    with POOL.connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            # autocommits, as psycopg_pool opens in autocommit

def execute_returning_one(sql:str, params:(str) = ()) -> None:
    with POOL.connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()
            # autocommits, as psycopg_pool opens in autocommit

def execute_returning_all(sql:str, params:(str) = ()) -> None:
    with POOL.connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
            # autocommits, as psycopg_pool opens in autocommit