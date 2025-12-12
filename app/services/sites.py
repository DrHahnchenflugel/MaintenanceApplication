from app.db import sites as sites_db

def list_sites():
    return sites_db.list_site_rows()
