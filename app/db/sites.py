from sqlalchemy import text
from app.db.connection import get_connection

def list_site_rows():
    sql = text("""
        SELECT
            id,
            shorthand,
            fullname
        FROM site
        ORDER BY fullname ASC, shorthand ASC
    """)

    with get_connection() as conn:
        rows = conn.execute(sql).mappings().all()

    return [dict(r) for r in rows]

def get_site_row(site_id):
    sql = text("""
        SELECT
            id,
            shorthand,
            fullname
        FROM site
        WHERE id = :id
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"id": site_id}).mappings().first()

    if row is None:
        return None

    return dict(row)

def site_shorthand_exists(shorthand: str) -> bool:
    sql = text("""
        SELECT 1
        FROM site
        WHERE UPPER(shorthand) = :shorthand
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"shorthand": shorthand}).mappings().first()

    return row is not None


def site_shorthand_exists_for_other_site(shorthand: str, *, exclude_site_id) -> bool:
    sql = text("""
        SELECT 1
        FROM site
        WHERE UPPER(shorthand) = :shorthand
          AND id <> :exclude_site_id
    """)

    with get_connection() as conn:
        row = conn.execute(
            sql,
            {
                "shorthand": shorthand,
                "exclude_site_id": exclude_site_id,
            },
        ).mappings().first()

    return row is not None


def create_site_row(*, shorthand: str, fullname: str):
    sql = text("""
        INSERT INTO site (
            shorthand,
            fullname
        )
        VALUES (
            :shorthand,
            :fullname
        )
        RETURNING
            id,
            shorthand,
            fullname
    """)

    with get_connection() as conn:
        row = conn.execute(
            sql,
            {
                "shorthand": shorthand,
                "fullname": fullname,
            },
        ).mappings().first()

    if row is None:
        raise RuntimeError("Failed to insert site")

    return dict(row)


def update_site_row(site_id, *, shorthand: str, fullname: str):
    sql = text("""
        UPDATE site
        SET
            shorthand = :shorthand,
            fullname = :fullname
        WHERE id = :id
        RETURNING
            id,
            shorthand,
            fullname
    """)

    with get_connection() as conn:
        row = conn.execute(
            sql,
            {
                "id": site_id,
                "shorthand": shorthand,
                "fullname": fullname,
            },
        ).mappings().first()

    if row is None:
        return None

    return dict(row)


def delete_site_row(site_id) -> bool:
    sql = text("""
        DELETE FROM site
        WHERE id = :id
    """)

    with get_connection() as conn:
        result = conn.execute(sql, {"id": site_id})

    return (result.rowcount or 0) > 0
