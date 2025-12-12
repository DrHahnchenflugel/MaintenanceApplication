from app.db import sites as sites_db

def list_sites():
    return sites_db.list_site_rows()

def get_site(site_id):
    return sites_db.get_site_row(site_id)
