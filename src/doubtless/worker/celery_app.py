from celery import Celery
from doubtless.config import REDIS_URL

celery_app = Celery("doubtless", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_track_started = True