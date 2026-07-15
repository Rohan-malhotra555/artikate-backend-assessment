from django.test import TestCase
from unittest.mock import patch
from celery.exceptions import Retry
from .utils import check_rate_limit, redis_client
from .tasks import send_order_email_task

from .models import Tenant, Customer, Order
from .context import current_tenant

# Create your tests here.

# SECTION 2: Rate-Limited Async Job Queue Architecture

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



# SECTION 3: MULTI-TENANCY MODELS


class TenantIsolationTests(TestCase):
    """
    SECTION 3: Multi-Tenant Data Isolation Tests
    """
    
    def setUp(self):
        # 1. THE SETUP (Creating the isolated data)
        self.apple = Tenant.objects.create(name="Apple")
        self.google = Tenant.objects.create(name="Google")
        
        self.steve = Customer.objects.create(name="Steve", email="steve@apple.com")
        self.sundar = Customer.objects.create(name="Sundar", email="sundar@google.com")
        
        self.apple_order = Order.objects.create(
            customer=self.steve, total_amount=100.00, tenant=self.apple
        )
        self.google_order = Order.objects.create(
            customer=self.sundar, total_amount=200.00, tenant=self.google
        )

    def test_objects_all_does_not_bypass_scoping(self):
        
        token = current_tenant.set(self.apple.id)
        
        orders = Order.objects.all() # The problem, .filter() is not there.
        
        # the trapdoor intercepted and only returned Apple's 1 order.
        self.assertEqual(orders.count(), 1)
        self.assertEqual(orders.first(), self.apple_order)
        
        current_tenant.reset(token)

    def test_tenant_cannot_access_other_tenant_data_explicitly(self):
        
        token = current_tenant.set(self.apple.id)
        
        # The View explicitly tries to steal Google's data
        stolen_orders = Order.objects.filter(tenant=self.google)
        

        # No record belongs to both apple and google.
        # So, (tenant=Apple AND tenant=Google), which is impossible, returning 0 results.
        self.assertEqual(stolen_orders.count(), 0)
        
        current_tenant.reset(token)