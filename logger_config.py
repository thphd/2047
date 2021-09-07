from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '%(levelname)s/%(module)s %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})
