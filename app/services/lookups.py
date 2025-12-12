from app.db import lookups as lookups_db

def list_asset_statuses():
    return lookups_db.list_asset_statuses()

def list_asset_categories():
    return lookups_db.list_asset_categories()
