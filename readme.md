# 2047

An attempt to bring 2049bbs.xyz back to life.

Backstory: [Silenced in China: The Archivists](https://www.hrw.org/news/2020/07/22/silenced-china-archivists)

In short, the former owner/webmaster of <https://2049bbs.xyz> was detained by the Chinese Government.

We decided to make a new forum titled 2047 that continues the legacy of 2049bbs.

## Steps

1. Install the dependencies. See `deploy.sh`

2. You can either restore the data from a database dump as described in `deploy.sh`, or parse the crawled backup files from https://github.com/2049bbs/2049bbs.github.io

  ```bash
  # download backup files
  cd parse
  git clone https://github.com/2049bbs/2049bbs.github.io

  # parse, put into DB, process
  python parse.py
  python standarize.py
  ```

5. access from browser: `127.0.0.1:5000`

## License

MIT
