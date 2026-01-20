from celery import Celery
import os

# RabbitMQ use nahi kar rahe, Redis use kar rahe hain as Broker and Backend
# Windows par Redis Docker ke through chalana padega
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    'rag_worker',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['src.worker.tasks']
)

app.conf.update(
    result_expires=3600,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    enable_utc=True, # STRICT UTC to fix drift
    timezone='UTC',
)

if __name__ == '__main__':
    app.start()
