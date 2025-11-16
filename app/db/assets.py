from sqlalchemy import text
from app.db.connection import get_connection

def get_asset_row(asset_id):
    """
    Fetch a single asset row by id.

    Args:
        asset_id: integer id from the `asset` table.

    Returns:
        dict with asset columns if found, otherwise None.

        Ex:
        {
            "id": 12,
            "variant_id": 3,
            "category_id": 4,
            "site_id": 1,
            "status_id": 1,
            "serial_num": "1234567890",
            "asset_tag": "EV3-RC-11",
            "acquired_at": ...,
            "retired_at": None,
            "retire_reason": None,
            "created_at": ...,
            "updated_at": ...
        }
    """

    sql = text("""
        SELECT
            id,
            variant_id,
            category_id,
            site_id,
            status_id,
            serial_num,
            asset_tag,
            acquired_at,
            retired_at,
            retire_reason,
            created_at,
            updated_at
        FROM asset
        WHERE id = :id
    """)

    with (get_connection() as conn):
        row = conn.execute(sql, {"id": asset_id})
        row = row.mappings()
        row = row.first()

    if row is None:
        return None

    return dict(row)
