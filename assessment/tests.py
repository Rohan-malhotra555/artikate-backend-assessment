from django.test import TestCase
from unittest.mock import patch
from celery.exceptions import Retry
from .utils import check_rate_limit, redis_client
from .tasks import send_order_email_task

# Create your tests here.

class JobQueueTests(TestCase):
    """
    SECTION 2: Rate-Limited Async Job Queue Tests
    """
    
    def setUp(self):

        redis_client.flushall()

    def test_rate_limiter_exactly_200_allowed(self):

        results = []
        for i in range(500):
            results.append(check_rate_limit())
        
        allowed_count = results.count(True)
        blocked_count = results.count(False)
        
        self.assertEqual(allowed_count, 200) # Proves the rate limit is NEVER exceeded
        self.assertEqual(blocked_count, 300) # Proves the remaining 300 are caught, not lost

    @patch('assessment.tasks.send_order_email_task.retry')
    def test_intentional_failure_triggers_retry(self, mock_retry):
        
        mock_retry.side_effect = Retry()
        
        for i in range(200):
            check_rate_limit()
            
        with self.assertRaises(Retry):
            send_order_email_task("test@artikate.com", "ORD-999")