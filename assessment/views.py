from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Order

# Create your views here.

class OrderSummaryAPIView(APIView):

    # SECTION 1: N+1 Query Problem Demonstration & Fix
    
    def get(self, request, *args, **kwargs):
        
        # THE BAD CODE (Demonstrating the N+1 Bug)
        # When we write this, Django will go to the database and will fetch all the records (.all()) in one trip.
        # Now, when each customer's name will be required while creating the summary down below (order.customer.name), 
        # then, for each record, Django will go, fetch the user, come back and repeat this for N times. Thus causing the 
        # N + 1 problem and the server crash.
        # orders = Order.objects.all()
        
        # THE FIXED CODE (WHY THIS WORKS)
        # select_related fetches the foreign key data in the same trip. This means, when the server goes to the Database to 
        # fetch the order objects, it says grab all order objects PLUS attach/staple the foreign key data, that is, the related table
        # data, which in this case is the Customer table's data, to each order object and then return the entire set of objects back to the code.
        # This way, only 1 trip to the Database covers the entire set of objects, including the joined Customer table data.
        
        orders = Order.objects.select_related('customer').all()

        summary = []
        
        for order in orders:
        
            summary.append({
                "order_id": order.id,
                "customer_name": order.customer.name, # N+1 triggers here if not pre-fetched using .select_related()
                "total": str(order.total_amount),
                "status": order.status
            })

        return Response({"count": len(summary), "data": summary})