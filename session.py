# because flask session is a total disaster

from itsdangerous import Signer
import os,json,base64
from base64 import b64encode,b64decode
from flask import request, g
from colors import *

from functools import lru_cache

def get_secret():
    fn = 'secret.bin'
    if os.path.exists(fn):
        f = open(fn, 'rb');r = f.read();f.close()
    else:
        r = os.urandom(32)
        f = open(fn, 'wb');f.write(r);f.close()
    return r

secret = get_secret()
signer = Signer(secret)

# rough implementation of JSON Web Signature (JWS)
def signj(json_object): # object -> utf8str
    json_str = json.dumps(json_object)
    json_bin = json_str.encode('utf-8')
    json_bin_b64 = b64encode(json_bin)
    json_bin_b64_signed_bin = signer.sign(json_bin_b64)
    json_bin_b64_signed_str = json_bin_b64_signed_bin.decode('utf-8')
    return json_bin_b64_signed_str

def unsignj(json_bin_b64_signed_str):
    return unsignj_cached(json_bin_b64_signed_str).copy()

@lru_cache(maxsize=4096)
def unsignj_cached(json_bin_b64_signed_str): # utf8str -> object
    json_bin_b64_signed_bin = json_bin_b64_signed_str.encode('utf-8')
    json_bin_b64 = signer.unsign(json_bin_b64_signed_bin)
    json_bin = b64decode(json_bin_b64)
    json_str = json_bin.decode('utf-8')
    json_object = json.loads(json_str)
    return json_object

def save_session(resp):
    curr_sess_string = get_current_session_str()
    newly_signed_sess_string = signj(g.session)

    if newly_signed_sess_string != curr_sess_string:

        print_down('save_session', g.session)

        resp.set_cookie(
            key='session',
            value=newly_signed_sess_string,
            max_age=86400*31,
            httponly=True,
            samesite='strict',
        )

def load_session():
    css = get_current_session_str()
    if not css: return {}
    try:
        return unsignj(css)
    except Exception as e:
        print_err('unsign err', e)
        return {}

def get_current_session_str():
    return request.cookies.get('session', default='')


def sign(s):
    return signer.sign(s.encode('utf-8'))

def unsign(s):
    try:
        u = signer.unsign(s)
        u = u.decode('utf-8')
    except Exception as e:
        return '{}'
    else:
        return u


if __name__ == '__main__':
    a = sign('helloworld')
    print(a)
    b = unsign(a)
    print(b)
    c = unsign(a+b'j')
    print(unsign(c))

    d = signj({1:2})
    e = unsignj(d)
    print(d)
    print(e)
