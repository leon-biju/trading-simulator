from celery import shared_task
from django.core.management import call_command


@shared_task
def flush_expired_tokens():
    """Remove expired JWT tokens from the blacklist table."""
    call_command('flushexpiredtokens')
