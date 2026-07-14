from django.db import models

# Create your models here.

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

    def __str__(self):
    
        return f"Order #{self.id} for {self.customer.name}"