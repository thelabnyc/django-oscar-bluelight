try:
    from .celery import app as celery_app  # noqa
except ImportError:
    pass
