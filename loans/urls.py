from django.urls import path
from rest_framework.routers import DefaultRouter

from loans.views import LoanAdminViewSet, LoanApplicationViewSet

router = DefaultRouter()

# router.register(r"loans", LoanApplicationViewSet, basename="loan-application")
# router.register(r"admin/loans", LoanAdminViewSet, basename="loan-admin")

urlpatterns = [
    path("loans/", LoanAdminViewSet.as_view({"get": "all_loans"}), name="all_loans"),
    path(
        "loans/<int:id>/",
        LoanAdminViewSet.as_view({"get": "retrieve_customer_loan"}),
        name="retrieve_customer_loan",
    ),
    path(
        "loans/<int:id>/approve/",
        LoanAdminViewSet.as_view({"post": "approve"}),
        name="approve_loan",
    ),
    path(
        "loans/<int:id>/reject/",
        LoanAdminViewSet.as_view({"post": "reject"}),
        name="reject_loan",
    ),
    path(
        "loans/<int:id>/flag/",
        LoanAdminViewSet.as_view({"post": "flag"}),
        name="flag_loan",
    ),
    path(
        "loans/flagged/",
        LoanAdminViewSet.as_view({"get": "flagged_loans"}),
        name="flagged_loans",
    ),
    # Customer URLs
    path(
        "loan/", LoanApplicationViewSet.as_view({"post": "submit"}), name="submit_loan"
    ),
    path(
        "loan/<int:id>/",
        LoanApplicationViewSet.as_view({"get": "retrieve_loan"}),
        name="retrieve_loan",
    ),
    path(
        "loans/requests/",
        LoanApplicationViewSet.as_view({"get": "my_applications"}),
        name="my_loans",
    ),
]
