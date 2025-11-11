from config.celery import app as celery_app



@celery_app.task
def update_market_data():
    print("HELLO FROM CELERY TASK: Updating market data...")