from commons import *
from api import register, es
from app import app

import sys
sys.path.append('./sb1024')
from sb1024 import sb1024_cc2_str_encrypt, sb1024_cc2_str_decrypt
@register('sb1024_encrypt')
def _():
    plain = es('plain')
    key = es('key')
    ct = sb1024_cc2_str_encrypt(key, plain)
    return {'ct': ct}

@register('sb1024_decrypt')
def _():
    ct = es('ct')
    key = es('key')
    plain = sb1024_cc2_str_decrypt(key, ct)
    return {'plain':plain}

@app.route('/sinocrypt')
def sinocrypt():
    return render_template_g(
        'sb1024.html.jinja',
        page_title='SinoCrypt',
    )
