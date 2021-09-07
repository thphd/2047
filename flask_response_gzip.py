import gzip, brotli
from io import BytesIO

from functools import lru_cache

from flask import request

from commons import *

@lru_cache(maxsize=512)
def zipthis(data, level):
    gzip_buffer = BytesIO()
    gzip_file = gzip.GzipFile(mode='wb', compresslevel=level, fileobj=gzip_buffer)
    gzip_file.write(data)
    gzip_file.close()
    return gzip_buffer.getvalue()

@lru_cache(maxsize=512)
def brothis(data, level=4):
    return brotli.compress(data,
        mode = 0,
        quality = level,
        lgwin = 22,
        lgblock = 0,
    )

# code borrowed from pypi package Flask-gzip
def gzipify(app):
    compress_level = 6
    minimum_size = 500

    def ar(response):
        ael = {i.strip() for i in request.headers.get('Accept-Encoding', '').lower().split(',')}

        import time
        t = time.time()

        rd = response.get_data()

        rh = response.headers
        ctype = rh['Content-Type']

        rsc = response.status_code

        def compare_size_and_log(alg, compressed):
            elapsed = int((time.time() - t)*1000)
            print_down(f'{alg} ({len(compressed)/len(rd)*100:.1f}%) '+
                f'{elapsed}ms {len(compressed)}/{len(rd)}')

        def compress_etag_response(format, data):
            if format=='br':
                compressed = brothis(data, 8)
            elif format=='gzip':
                compressed = zipthis(data, 6)

            compare_size_and_log(format, compressed)

            response.set_data(compressed)

            rh['Content-Encoding'] = format
            rh['Content-Length'] = len(compressed)
            etag304(response)

            return response

        if (rsc < 200 or rsc >= 300
            or response.direct_passthrough
            or len(rd) < minimum_size
            or ('br' not in ael and 'gzip' not in ael)
            or 'Content-Encoding' in rh
            or 'image' in ctype
            ):
            pass

        elif 'br' in ael:
            response = compress_etag_response('br', rd)

        elif 'gzip' in ael:
            response = compress_etag_response('gzip', rd)

        return response

    app.after_request(ar)
