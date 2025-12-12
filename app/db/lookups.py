from app.db.db import query_all

def list_asset_statuses():
    sql = """
        select
            asset_status_id,
            code,
            display_name,
            display_order
        from asset_statuses
        order by display_order asc, display_name asc
    """
    return query_all(sql)

def list_asset_categories():
    sql = """
        select
            asset_category_id,
            code,
            display_name,
            display_order
        from asset_categories
        order by display_order asc, display_name asc
    """
    return query_all(sql)
