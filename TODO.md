# UNPRIORITISED
- update env variable file to be able to be external (dont mandate that its in the same folder, e.g., ../env)
- add make as a prerequisite (which is apparently not always there on ubuntu server?)
- add chmod +x as a step on setting the makefiles up
- update .env.example to not always point to localhost, the db is likely not on a localhost
- in the db, make name vs label make more user-friendly (which is userfriendly name which is internal name) 
  - also name=code (asset status)
- evaluate setting app/db/assets>list_asset_rows>args>asset_tag from literal equates to ilike 

# DONE
- update .env.example file to be more user friendly. consider key=value DSN instead of URL encoding.
