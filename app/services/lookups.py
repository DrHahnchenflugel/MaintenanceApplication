from app.db import lookups as lookups_db

def list_asset_statuses():
    return lookups_db.list_asset_status_rows()

def list_asset_categories():
    return lookups_db.list_category_rows()

def list_makes(category_id=None):
    return lookups_db.list_makes(category_id=category_id)