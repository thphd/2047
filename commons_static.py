import os, hashlib, binascii as ba
import base64, re
import time, math
from colors import *
# from functools import lru_cache

from cachetools.func import *
from cachy import stale_cache

def iif(a,b,c):return b if a else c

import json
def obj2json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)

@stale_cache(ttr=1, ttl=30)
def readfile(fn, mode='rb', *a, **kw):
    if 'b' not in mode:
        with open(fn, mode, encoding='utf8', *a, **kw) as f:
            return f.read()
    else:
        with open(fn, mode, *a, **kw) as f:
            return f.read()

def writefile(fn, data, mode='wb', encoding='utf8', *a, **kw):
    if 'b' not in mode:
        with open(fn,mode, encoding=encoding, *a,**kw) as f:
            f.write(data)
    else:
        with open(fn,mode,*a,**kw) as f:
            f.write(data)

def removefile(fn):
    try:
        os.remove(fn)
    except Exception as e:
        print(e)
        print('failed to remove', fn)
    else:
        return

import threading

def dispatch(f):
    t = threading.Thread(target=f, daemon=True)
    t.start()

def init_directory(d):
    try:
        os.mkdir(d)
    except FileExistsError as e:
        print_err('directory {} already exists.'.format(d), e)
    else:
        print_info('directory {} created.'.format(d))

def key(d, k):
    if k in d:
        return d[k]
    else:
        return None

def intify(s, name=''):
    try:
        return int(s)
    except:
        if s:
            # print_err('intifys',s,name)
            pass
        return 0

def get_environ(k):
    k = k.upper()
    if k in os.environ:
        return os.environ[k]
    else:
        return None

def clip(a,b):
    def _clip(c):
        return min(b,max(a, c))
    return _clip

clip01 = clip(0,1)
