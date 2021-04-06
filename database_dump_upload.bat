arangodump --output-directory dump --server.database db2047 --server.password "" --overwrite true --log.color false

rem # arangodump --output-directory dump_pmf --server.database dbpmf --server.password "" --overwrite true --log.color false

set https_proxy=localhost:1080
# assume you have the right github token stored in release_token.txt
python make_archive_backup_release.py --upload

timeout 10
