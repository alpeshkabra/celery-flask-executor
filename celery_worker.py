from flask_app import celery
from flask_app import add_together


if __name__ == '__main__':
    celery.start()
