# 2047

An attempt to bring 2049bbs.xyz back to life.

Backstory: [Silenced in China: The Archivists](https://www.hrw.org/news/2020/07/22/silenced-china-archivists)

## Steps

No database file of 2049bbs.xyz available, using crawled backup from https://github.com/2049bbs/2049bbs.github.io

1. install ArangoDB 3.7 and Python 3.7

2.  ```bash
    git clone <this>

    # download backup files
    cd parse
    git clone https://github.com/2049bbs/2049bbs.github.io

    # parse, put into DB, process
    python parse.py
    python standarize.py
    ```

3.  ```bash
    pip install <dependencies>
    python main.py
    ```
4.  access from browser: `127.0.0.1:5000`

## Special dependencies

- tl;dr you can't install them from pypi
- https://github.com/flavono123/identicon
