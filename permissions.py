from rest_framework import permissions

from loans.models import LoanApplication


class IsLoanAdmin(permissions.BasePermission):
    """
    Admin-level permission class for loan admin actions.

    Only allows access to users with admin privileges.
    """

    def has_permission(self, request, view):
        return request.user.role == "ADMIN" or request.user.is_superuser


class IsCustomer(permissions.BasePermission):
    # makes sure user is a customer and can view their own loans.
    def has_permission(self, request, view):
        if request.user.role == "CUSTOMER":
            if view.action == "retrieve":  # Allow view only if it's their own loan
                loan_id = view.kwargs.get("pk")
                try:
                    loan = LoanApplication.objects.get(id=loan_id)
                    return loan.user == request.user
                except LoanApplication.DoesNotExist:
                    # user does not have access to this loan
                    return False
        return True
