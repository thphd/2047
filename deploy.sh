# this script has been tested on ubuntu 1604

# install arangodb

wget https://download.arangodb.com/arangodb37/Community/Linux/arangodb3_3.7.1-1_amd64.deb

wget https://download.arangodb.com/arangodb37/Community/Linux/arangodb3-client_3.7.1-1_amd64.deb

apt install ./arango*.deb
apt install ./arango*client*.deb

systemctl unmask arangodb3
systemctl start arangodb3

# install screen

apt-get update
apt-get install screen

# install python

apt update
add-apt-repository ppa:deadsnakes/ppa
apt update
apt install python3.7
apt install python3-pip

# code
git clone https://github.com/thphd/2047
python3.7 -m pip install --upgrade pip
python3.7 -m pip install termcolor
python3.7 -m pip install colorama
python3.7 -m pip install markdown2
python3.7 -m pip install pillow
python3.7 -m pip install Flask
python3.7 -m pip install flask_cors
python3.7 -m pip install Flask_gzip

git clone https://github.com/flavono123/identicon
python3.7 -m pip install -e ./identicon

# upload the backup to ./2047/dump
# run ./database_restore.bat to load data from the backup

# cd 2047
# python3.7 main.py

# access from browser @ localhost:5000
