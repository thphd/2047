# from flask_cors import CORS

import flask
from flask import Flask, g, abort # session

# FUCK YOU, FLASK
# https://github.com/pallets/flask/issues/2989#issuecomment-695412677
class FlaskPatched(Flask):
    def select_jinja_autoescape(self, filename):
        """Returns ``True`` if autoescaping should be active for the given
        template name. If no template name is given, returns `True`.

        .. versionadded:: 0.5
        """
        if filename is None:
            return True
        return filename.endswith(('.html', '.htm', '.xml', '.xhtml', 'html.jinja'))

from flask import render_template, request, send_from_directory, make_response
# from flask_gzip import Gzip

from werkzeug.middleware.proxy_fix import ProxyFix

app = FlaskPatched(__name__, static_url_path='')

app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

# CORS(app)
from flask_response_gzip import gzipify
gzipify(app)
