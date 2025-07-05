from rest_framework.routers import DefaultRouter

from loans.views import LoanAdminViewSet, LoanApplicationViewSet

router = DefaultRouter()

router.register(r"loans", LoanApplicationViewSet, basename="loan-application")
router.register(r"admin/loans", LoanAdminViewSet, basename="loan-admin")

urlpatterns = [] + router.urls
