rem dump repeatedly 

timeout /t 10

:loop

arangodump --output-directory dump --server.database db2047 --server.password "" --overwrite true --log.color false

# assume you have the right github token stored in release_token.txt
python make_archive_backup_release.py
python make_archive_delete_older.py

timeout /t 600

goto loop