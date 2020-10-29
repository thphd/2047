:loop

timeout /t 1800

arangodump --output-directory dump --server.database db2047 --server.password "" --overwrite true --log.color false

# assume you have the right github token stored in release_token.txt
python make_archive_backup_release.py

goto loop