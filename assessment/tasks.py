from celery import shared_task
from .utils import check_rate_limit


@shared_task(bind=True, acks_late=True, max_retries=5)
def send_order_email_task(self, user_email, order_id):
    """
    SECTION 2: Rate-Limited Async Task
    """
    
    is_allowed = check_rate_limit()

    if not is_allowed:
       
        backoff_seconds = 60 * (2 ** self.request.retries)
        
        print(f"Rate limit hit. Retrying in {backoff_seconds} seconds...")
        
        raise self.retry(countdown=backoff_seconds)

    # The production (real) email code goes here.
    success_message = f"Email successfully sent to {user_email} for Order {order_id}"

    print(success_message)
    
    return success_message