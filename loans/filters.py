import django_filters.rest_framework as filters

from loans.models import LoanApplication


class LoanApplicationFilter(filters.FilterSet):
    """
    Filter set for LoanApplication model
    """

    date_applied_after = filters.DateFilter(
        field_name="date_applied", lookup_expr="gte"
    )
    date_applied_before = filters.DateFilter(
        field_name="date_applied", lookup_expr="lte"
    )
    status = filters.CharFilter(field_name="status")
    user_email = filters.CharFilter(field_name="user__email", lookup_expr="icontains")

    class Meta:
        model = LoanApplication
        fields = ["status", "user_email", "date_applied_after", "date_applied_before"]
