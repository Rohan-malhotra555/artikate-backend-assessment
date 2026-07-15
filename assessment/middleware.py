from .context import current_tenant

class TenantMiddleware:
    """
    SECTION 3: Multi-Tenant Data Isolation Middleware
    """
    
    def __init__(self, get_response):

        self.get_response = get_response

    def __call__(self, request):

        tenant_id = request.META.get('HTTP_X_TENANT_ID')

        if tenant_id:

            token = current_tenant.set(tenant_id)

        response = self.get_response(request)


        if tenant_id:
            current_tenant.reset(token)

        return response