"""
Celery application configuration for PropIQ async task processing.
Uses Redis as the message broker and result backend.
"""

import os
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "propiq",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.core.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,        # 5 minute hard limit
    task_soft_time_limit=240,   # 4 minute soft limit
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)
