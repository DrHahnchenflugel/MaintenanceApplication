from app.db.db import query_all

def list_sites(page: int = 1, page_size: int = 50):
    offset = (page - 1) * page_size
    sql = """
        select
            site_id,
            site_code,
            site_name
        from sites
        order by site_name asc
        limit %s offset %s
    """
    return query_all(sql, (page_size, offset))
