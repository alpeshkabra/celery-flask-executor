from flask import Flask
from celery import Celery
from celery.result import AsyncResult
import os


def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def create_app():
    app = Flask(__name__)
    app.config.update(
        CELERY_BROKER_URL=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
        CELERY_RESULT_BACKEND=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
    )

    celery = make_celery(app)

    @app.route('/add/<int:a>/<int:b>')
    def add(a, b):
        task = add_together.apply_async(args=[a, b])
        return {'task_id': task.id}, 202

    @app.route('/result/<task_id>')
    def result(task_id):
        task_result = AsyncResult(task_id)
        response = {'state': task_result.state}

        if task_result.state == 'PENDING':
            response.update({
                'current': 0,
                'total': 1,
                'status': 'Pending...'
            })
        elif task_result.state != 'FAILURE':
            result_info = task_result.info
            if isinstance(result_info, dict):
                response.update({
                    'current': result_info.get('current', 0),
                    'total': result_info.get('total', 1),
                    'status': result_info.get('status', ''),
                    'result': task_result.result
                })
            else:
                response.update({
                    'current': 1,
                    'total': 1,
                    'status': '',
                    'result': task_result.result
                })
        else:
            response.update({
                'current': 1,
                'total': 1,
                'status': str(task_result.info),
            })
        return response

    @app.route('/')
    def home():
        return 'Hello World'

    return app


app = create_app()
celery = make_celery(app)


@celery.task()
def add_together(a, b):
    return a + b
