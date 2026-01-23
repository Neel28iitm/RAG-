@echo off
echo Starting Celery Worker...
celery -A src.worker.celery_app worker --loglevel=info -P solo --concurrency=1
pause
