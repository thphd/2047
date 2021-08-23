# this script should be run on an instance of ubuntu 1604/1804
# assume you already cloned the repo
# assume you start this script via ./2047/deploy.sh

# install [latest stable version of] arangodb

wget https://download.arangodb.com/nightly/3.7/Linux/arangodb3_3.7.3~~nightly-1_amd64.deb

dpkg -i arangodb3_3.7.1-1_amd64.deb

systemctl unmask arangodb3
systemctl start arangodb3

# install screen

apt update
apt --assume-yes install screen

# install python

apt update
add-apt-repository --yes ppa:deadsnakes/ppa
apt update
apt --assume-yes install python3.7
apt --assume-yes install python3-pip

# code
git clone https://github.com/thphd/2047
python3.7 -m pip install --upgrade pip
python3.7 -m pip install termcolor cachetools flask-threads
python3.7 -m pip install colorama
# python3.7 -m pip install markdown2
python3.7 -m pip install mistletoe beautifulsoup4 python-snappy cryptography
python3.7 -m pip install pillow
python3.7 -m pip install Flask
python3.7 -m pip install flask_cors
# python3.7 -m pip install Flask_gzip
python3.7 -m pip install githubrelease
python3.7 -m pip install qrcode
python3.7 -m pip install forbiddenfruit

git clone https://github.com/flavono123/identicon
python3.7 -m pip install -e ./identicon

# upload the dumped database backup files to ./2047/dump
# cd 2047
# run ./database_restore.bat to load data from the backup

# python3.7 main.py

# access from browser @ localhost:5000
