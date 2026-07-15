from django.db import models
from .context import current_tenant

# Create your models here.


# SECTION 3: MULTI-TENANCY MODELS

class Tenant(models.Model):

    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class TenantManager(models.Manager):
    """
    The custom manager that acts as the Trapdoor. 
    It intercepts all queries and filters them by the current tenant.
    """
    def get_queryset(self):

        queryset = super().get_queryset()

        tenant_id = current_tenant.get()
        
        if tenant_id:
            # Forcefully filtering the data using the tenant_id at the ORM level.
            return queryset.filter(tenant_id=tenant_id)
            
        return queryset


# EXISTING MODELS (UPDATED)    

class Customer(models.Model):

    name = models.CharField(max_length=255)

    email = models.EmailField(unique=True)

    def __str__(self):
        
        return self.name

class Order(models.Model):

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    status = models.CharField(max_length=50, default='Pending')


    # --- SECTION 3 ADDITIONS ---
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    
    # Replace the default search engine with our custom trapdoor
    objects = TenantManager()

    def __str__(self):
    
        return f"Order #{self.id} for {self.customer.name}"