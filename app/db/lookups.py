from sqlalchemy import text

from app.db.connection import get_connection


def list_category_rows():
    sql = text("""
        SELECT
            id,
            name,
            label
        FROM category
        ORDER BY label ASC, name ASC
    """)

    with get_connection() as conn:
        rows = conn.execute(sql).mappings().all()

    return [dict(r) for r in rows]


def get_category_row(category_id):
    sql = text("""
        SELECT
            id,
            name,
            label
        FROM category
        WHERE id = :id
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"id": category_id}).mappings().first()

    return None if row is None else dict(row)


def category_name_exists(name: str, *, exclude_id=None) -> bool:
    sql = """
        SELECT 1
        FROM category
        WHERE (
            LOWER(name) = LOWER(:name)
            OR LOWER(label) = LOWER(:name)
        )
    """

    params = {"name": name}
    if exclude_id is not None:
        sql += " AND id <> :exclude_id"
        params["exclude_id"] = exclude_id

    with get_connection() as conn:
        row = conn.execute(text(sql), params).mappings().first()

    return row is not None


def create_category_row(*, name: str, label: str):
    sql = text("""
        INSERT INTO category (
            name,
            label
        )
        VALUES (
            :name,
            :label
        )
        RETURNING
            id,
            name,
            label
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"name": name, "label": label}).mappings().first()

    if row is None:
        raise RuntimeError("Failed to insert category")

    return dict(row)


def update_category_row(category_id, *, name: str, label: str):
    sql = text("""
        UPDATE category
        SET
            name = :name,
            label = :label
        WHERE id = :id
        RETURNING
            id,
            name,
            label
    """)

    with get_connection() as conn:
        row = conn.execute(
            sql,
            {
                "id": category_id,
                "name": name,
                "label": label,
            },
        ).mappings().first()

    return None if row is None else dict(row)


def delete_category_row(category_id) -> bool:
    sql = text("""
        DELETE FROM category
        WHERE id = :id
    """)

    with get_connection() as conn:
        result = conn.execute(sql, {"id": category_id})

    return (result.rowcount or 0) > 0


def list_makes(category_id=None):
    sql = """
        SELECT
            make.id,
            make.name,
            make.label,
            make.category_id,
            category.name AS category_name,
            category.label AS category_label
        FROM make
        LEFT JOIN category
          ON make.category_id = category.id
    """

    params = {}
    if category_id:
        sql += " WHERE make.category_id = :category_id"
        params["category_id"] = category_id

    sql += """
        ORDER BY
            COALESCE(category.label, category.name, '') ASC,
            COALESCE(make.label, make.name, '') ASC,
            make.name ASC
    """

    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return [dict(r) for r in rows]


def get_make_row(make_id):
    sql = text("""
        SELECT
            make.id,
            make.name,
            make.label,
            make.category_id,
            category.name AS category_name,
            category.label AS category_label
        FROM make
        LEFT JOIN category
          ON make.category_id = category.id
        WHERE make.id = :id
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"id": make_id}).mappings().first()

    return None if row is None else dict(row)


def make_name_exists(name: str, *, exclude_id=None) -> bool:
    sql = """
        SELECT 1
        FROM make
        WHERE (
            LOWER(name) = LOWER(:name)
            OR LOWER(label) = LOWER(:name)
        )
    """

    params = {"name": name}
    if exclude_id is not None:
        sql += " AND id <> :exclude_id"
        params["exclude_id"] = exclude_id

    with get_connection() as conn:
        row = conn.execute(text(sql), params).mappings().first()

    return row is not None


def create_make_row(*, category_id, name: str, label: str):
    sql = text("""
        INSERT INTO make (
            category_id,
            name,
            label
        )
        VALUES (
            :category_id,
            :name,
            :label
        )
        RETURNING
            id,
            category_id,
            name,
            label
    """)

    with get_connection() as conn:
        row = conn.execute(
            sql,
            {
                "category_id": category_id,
                "name": name,
                "label": label,
            },
        ).mappings().first()

    if row is None:
        raise RuntimeError("Failed to insert make")

    return dict(row)


def update_make_row(make_id, *, category_id, name: str, label: str):
    sql = text("""
        UPDATE make
        SET
            category_id = :category_id,
            name = :name,
            label = :label
        WHERE id = :id
        RETURNING
            id,
            category_id,
            name,
            label
    """)

    with get_connection() as conn:
        row = conn.execute(
            sql,
            {
                "id": make_id,
                "category_id": category_id,
                "name": name,
                "label": label,
            },
        ).mappings().first()

    return None if row is None else dict(row)


def delete_make_row(make_id) -> bool:
    sql = text("""
        DELETE FROM make
        WHERE id = :id
    """)

    with get_connection() as conn:
        result = conn.execute(sql, {"id": make_id})

    return (result.rowcount or 0) > 0


def list_models(make_id=None):
    sql = """
        SELECT
            model.id,
            model.name,
            model.label,
            model.make_id,
            make.name AS make_name,
            make.label AS make_label,
            make.category_id AS category_id,
            category.name AS category_name,
            category.label AS category_label
        FROM model
        LEFT JOIN make
          ON model.make_id = make.id
        LEFT JOIN category
          ON make.category_id = category.id
    """

    params = {}
    if make_id:
        sql += " WHERE model.make_id = :make_id"
        params["make_id"] = make_id

    sql += """
        ORDER BY
            COALESCE(make.label, make.name, '') ASC,
            COALESCE(model.label, model.name, '') ASC,
            model.name ASC
    """

    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return [dict(r) for r in rows]


def get_model_row(model_id):
    sql = text("""
        SELECT
            model.id,
            model.name,
            model.label,
            model.make_id,
            make.name AS make_name,
            make.label AS make_label,
            make.category_id AS category_id,
            category.name AS category_name,
            category.label AS category_label
        FROM model
        LEFT JOIN make
          ON model.make_id = make.id
        LEFT JOIN category
          ON make.category_id = category.id
        WHERE model.id = :id
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"id": model_id}).mappings().first()

    return None if row is None else dict(row)


def model_name_exists_in_make(name: str, make_id, *, exclude_id=None) -> bool:
    sql = """
        SELECT 1
        FROM model
        WHERE make_id = :make_id
          AND (
            LOWER(name) = LOWER(:name)
            OR LOWER(label) = LOWER(:name)
          )
    """

    params = {
        "make_id": make_id,
        "name": name,
    }
    if exclude_id is not None:
        sql += " AND id <> :exclude_id"
        params["exclude_id"] = exclude_id

    with get_connection() as conn:
        row = conn.execute(text(sql), params).mappings().first()

    return row is not None


def create_model_row(*, make_id, name: str, label: str):
    sql = text("""
        INSERT INTO model (
            make_id,
            name,
            label
        )
        VALUES (
            :make_id,
            :name,
            :label
        )
        RETURNING
            id,
            make_id,
            name,
            label
    """)

    with get_connection() as conn:
        row = conn.execute(
            sql,
            {
                "make_id": make_id,
                "name": name,
                "label": label,
            },
        ).mappings().first()

    if row is None:
        raise RuntimeError("Failed to insert model")

    return dict(row)


def update_model_row(model_id, *, make_id, name: str, label: str):
    sql = text("""
        UPDATE model
        SET
            make_id = :make_id,
            name = :name,
            label = :label
        WHERE id = :id
        RETURNING
            id,
            make_id,
            name,
            label
    """)

    with get_connection() as conn:
        row = conn.execute(
            sql,
            {
                "id": model_id,
                "make_id": make_id,
                "name": name,
                "label": label,
            },
        ).mappings().first()

    return None if row is None else dict(row)


def delete_model_row(model_id) -> bool:
    sql = text("""
        DELETE FROM model
        WHERE id = :id
    """)

    with get_connection() as conn:
        result = conn.execute(sql, {"id": model_id})

    return (result.rowcount or 0) > 0


def list_variants(model_id=None):
    sql = """
        SELECT
            variant.id,
            variant.name,
            variant.label,
            variant.model_id,
            model.name AS model_name,
            model.label AS model_label,
            model.make_id AS make_id,
            make.name AS make_name,
            make.label AS make_label,
            make.category_id AS category_id,
            category.name AS category_name,
            category.label AS category_label
        FROM variant
        LEFT JOIN model
          ON variant.model_id = model.id
        LEFT JOIN make
          ON model.make_id = make.id
        LEFT JOIN category
          ON make.category_id = category.id
    """

    params = {}
    if model_id:
        sql += " WHERE variant.model_id = :model_id"
        params["model_id"] = model_id

    sql += """
        ORDER BY
            COALESCE(make.label, make.name, '') ASC,
            COALESCE(model.label, model.name, '') ASC,
            COALESCE(variant.label, variant.name, '') ASC,
            variant.name ASC
    """

    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return [dict(r) for r in rows]


def get_variant_row(variant_id):
    sql = text("""
        SELECT
            variant.id,
            variant.name,
            variant.label,
            variant.model_id,
            model.name AS model_name,
            model.label AS model_label,
            model.make_id AS make_id,
            make.name AS make_name,
            make.label AS make_label,
            make.category_id AS category_id,
            category.name AS category_name,
            category.label AS category_label
        FROM variant
        LEFT JOIN model
          ON variant.model_id = model.id
        LEFT JOIN make
          ON model.make_id = make.id
        LEFT JOIN category
          ON make.category_id = category.id
        WHERE variant.id = :id
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"id": variant_id}).mappings().first()

    return None if row is None else dict(row)


def variant_name_exists_in_model(name: str, model_id, *, exclude_id=None) -> bool:
    sql = """
        SELECT 1
        FROM variant
        WHERE model_id = :model_id
          AND (
            LOWER(name) = LOWER(:name)
            OR LOWER(label) = LOWER(:name)
          )
    """

    params = {
        "model_id": model_id,
        "name": name,
    }
    if exclude_id is not None:
        sql += " AND id <> :exclude_id"
        params["exclude_id"] = exclude_id

    with get_connection() as conn:
        row = conn.execute(text(sql), params).mappings().first()

    return row is not None


def create_variant_row(*, model_id, name: str, label: str):
    sql = text("""
        INSERT INTO variant (
            model_id,
            name,
            label
        )
        VALUES (
            :model_id,
            :name,
            :label
        )
        RETURNING
            id,
            model_id,
            name,
            label
    """)

    with get_connection() as conn:
        row = conn.execute(
            sql,
            {
                "model_id": model_id,
                "name": name,
                "label": label,
            },
        ).mappings().first()

    if row is None:
        raise RuntimeError("Failed to insert variant")

    return dict(row)


def update_variant_row(variant_id, *, model_id, name: str, label: str):
    sql = text("""
        UPDATE variant
        SET
            model_id = :model_id,
            name = :name,
            label = :label
        WHERE id = :id
        RETURNING
            id,
            model_id,
            name,
            label
    """)

    with get_connection() as conn:
        row = conn.execute(
            sql,
            {
                "id": variant_id,
                "model_id": model_id,
                "name": name,
                "label": label,
            },
        ).mappings().first()

    return None if row is None else dict(row)


def delete_variant_row(variant_id) -> bool:
    sql = text("""
        DELETE FROM variant
        WHERE id = :id
    """)

    with get_connection() as conn:
        result = conn.execute(sql, {"id": variant_id})

    return (result.rowcount or 0) > 0


def list_issue_status_rows():
    sql = text("""
        SELECT
            id,
            code,
            label,
            display_order
        FROM issue_status
        ORDER BY display_order ASC
    """)

    with get_connection() as conn:
        rows = conn.execute(sql).mappings().all()

    return [dict(r) for r in rows]
