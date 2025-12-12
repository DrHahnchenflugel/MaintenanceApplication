from app.db import sites as sites_db

def list_sites(page: int = 1, page_size: int = 50):
    return sites_db.list_sites(page=page, page_size=page_size)
