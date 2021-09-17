import os, hashlib, binascii as ba
import base64, re
import time, math
from colors import *
# from functools import lru_cache
from numba import jit

from cachetools.func import *
from cachy import *

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
        print_err(e)
        print_err('failed to remove', fn)
    else:
        return

import threading

def dispatch(f):
    return tpe.submit(f)
    # t = AppContextThreadMod(target=f, daemon=True)
    # # t = threading.Thread(target=f, daemon=True)
    # t.start()

def dispatch_with_retries(f):
    n = 0
    def wrapper():
        nonlocal n
        while 1:
            try:
                f()
            except Exception as e:
                print_err(e)
                n+=1
                time.sleep(0.5)
                print_up(f'{f.__name__}() retry #{n}')
            else:
                print_down(f'{f.__name__}() success on attempt #{n}')
                break
    return tpe.submit(wrapper)

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

def floatify(s):
    try:
        return float(s)
    except:
        if s:
            pass
        return 0.

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

import zlib

def calculate_checksum(bin): return zlib.adler32(bin).to_bytes(4,'big')

def calculate_checksum_base64(bin):
    csum = calculate_checksum(bin)
    chksum_encoded = base64.b64encode(csum).decode('ascii')
    return chksum_encoded

def calculate_checksum_base64_replaced(bin):
    return calculate_checksum_base64(bin).replace('+','-').replace('/','_')

def calculate_etag(bin):
    return calculate_checksum_base64_replaced(bin)


# pw hashing

def bytes2hexstr(b):
    return ba.b2a_hex(b).decode('ascii')

def hexstr2bytes(h):
    return ba.a2b_hex(h.encode('ascii'))

# https://nitratine.net/blog/post/how-to-hash-passwords-in-python/
def get_salt():
    return os.urandom(32)

def get_random_hex_string(b=8):
    return base64.b16encode(os.urandom(b)).decode('ascii')

def hash_pw(salt, string):
    return hashlib.pbkdf2_hmac(
        'sha256',
        string.encode('ascii'),
        salt,
        100000,
    )

# input string, output hash and salt
def hash_w_salt(string):
    salt = get_salt()
    hash = hash_pw(salt, string)
    return bytes2hexstr(hash), bytes2hexstr(salt)

# input hash,salt,string, output comparison result
def check_hash_salt_pw(hashstr, saltstr, string):
    chash = hash_pw(hexstr2bytes(saltstr), string)
    return chash == hexstr2bytes(hashstr)


def timethis(stmt):
    import re, timeit
    print('timing', stmt)
    broken = re.findall(f'\$([a-zA-Z][0-9a-zA-Z_\-]*)', stmt)
    stmt = stmt.replace('$','')
    setup = f"from __main__ import {','.join(broken)}"

    exec(setup) # preheat
    exec(stmt)

    timeit.Timer(stmt,
        setup=setup
        ).autorange(
            lambda a,b:print(f'{a} in {b:.4f}, avg: {b/a*1000_000:.4f}us'))

# if __name__ == '__main__':
#     k = time.time()
#     def hello():
#         if time.time() - k < 2:
#             raise Exception('nah')
#
#     dispatch_with_retries(hello)
#     time.sleep(4)

if __name__ == '__main__':
    toenc = b"r12uf-398gy309ghh123r1"*100000
    timethis('calculate_checksum_base64_replaced(toenc)')
