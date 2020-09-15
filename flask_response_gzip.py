import gzip
from io import BytesIO

from functools import lru_cache
from flask import request

@lru_cache(maxsize=4096)
def zipthis(data, level):
    gzip_buffer = BytesIO()
    gzip_file = gzip.GzipFile(mode='wb', compresslevel=level, fileobj=gzip_buffer)
    gzip_file.write(data)
    gzip_file.close()
    return gzip_buffer.getvalue()

# code borrowed from pypi package Flask-gzip
def gzipify(app):
    compress_level = 6
    minimum_size = 500

    def ar(response):
        accept_encoding = request.headers.get('Accept-Encoding', '')

        if 'gzip' not in accept_encoding.lower():
            print('request does not accept gzip')

        if response.status_code < 200 or \
            response.status_code >= 300 or \
            response.direct_passthrough or \
            len(response.get_data()) < minimum_size or \
            'gzip' not in accept_encoding.lower() or \
            'Content-Encoding' in response.headers:
            return response

        response.set_data(zipthis(response.get_data(), compress_level))
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = len(response.get_data())
        return response

    app.after_request(ar)
