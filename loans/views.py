from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from fraud.services import FraudDetectionError
from loans.models import LoanApplication
from loans.serializers import LoanApplicationResponse, LoanApplicationSerializer
from loans.services import LoanApplicationError, LoanManagementService
from permissions import IsCustomer, IsLoanAdmin

from .serializers import LoanApplicationRequest


@extend_schema(
    tags=["Loans"],
)
class LoanApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing loan applications.
    Provides CRUD operations and additional actions for loan applications.
    """

    permission_classes = [IsCustomer]
    http_method_names = ["get", "post"]

    serializer_class = LoanApplicationRequest

    # Override this to prevent 'list' from appearing
    def get_queryset(self):
        raise PermissionDenied("This action is not available.")

    # Override this to prevent 'create' from appearing
    def create(self, request, *args, **kwargs):
        raise PermissionDenied("This action is not available.")

    @extend_schema(
        summary="Retrieve a specific loan application by ID",
        responses={
            200: OpenApiResponse(),
            404: OpenApiResponse(description="Loan application not found"),
            403: OpenApiResponse(description="Permission denied"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @action(detail=False, methods=["get"], url_path="requests")
    def my_applications(self, request):
        """
        Retrieve all loan applications for the authenticated user.
        """
        user = request.user
        applications = user.loan_applications.all()
        serializer = LoanApplicationResponse(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Submit a new loan application",
        responses={
            201: OpenApiResponse(description="Loan application created successfully"),
            400: OpenApiResponse(description="Invalid request data"),
            403: OpenApiResponse(description="Permission denied"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @action(detail=False, methods="post", url_path="loan")
    def submit(self, request, *args, **kwargs):
        """
        Submit a new application

        Validates the request data and creates a new loan application for the authenticated user.
        """
        from loans import services as loan_service

        user = request.user

        serializer = LoanApplicationRequest(data=request.data)
        serializer.is_valid(raise_exception=True)

        loan_data = serializer.validated_data

        try:
            loan = loan_service.submit_loan(
                user, amount=loan_data["amount_requested"], purpose=loan_data["purpose"]
            )
            loan_response = LoanApplicationResponse(loan)
            return Response(loan_response, status=status.HTTP_201_CREATED)
        except FraudDetectionError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["Loans"],
)
class LoanAdminViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing loan applications in the admin interface.
    Provides CRUD operations for loan applications.
    """

    permission_classes = [IsLoanAdmin, permissions.IsAuthenticated]
    http_method_names = ["get", "post"]

    @classmethod
    def get_extra_actions(cls):
        """
        Overriding this method allows us to remove unwanted actions
        such as `create` or `list` from the schema.

        Ref: https://www.cdrf.co/3.14/rest_framework.viewsets/ModelViewSet.html#get_extra_actions
        """
        return []

    @action(detail=True, methods=["get"], url_path="loan")
    def retrieve_loan(self, request, pk=None):
        """
        Admin views a specific loan application by ID.
        """
        loan = self.get_object()
        serializer = LoanApplicationSerializer(loan)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    @extend_schema(
        summary="Retrieve all loan applications",
        responses={
            200: OpenApiResponse(),
            404: OpenApiResponse(description="No loan applications found"),
            403: OpenApiResponse(description="Permission denied"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def all_loans(self, request):
        """
        Admin can view all loan applications.
        """
        loans = LoanApplication.objects.all()
        serializer = LoanApplicationSerializer(loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="approve")
    @extend_schema(
        description="Approve a loan application",
        responses={
            200: OpenApiResponse(description="Loan application approved"),
            400: OpenApiResponse(description="Error approving loan application"),
            403: OpenApiResponse(description="Permission denied"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def approve(self, request, pk=None):
        """
        Admin approves a loan application.
        """
        if not pk:
            return Response(
                {"error": "Loan ID is required for approval."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        loan_service = LoanManagementService()
        try:
            loan = loan_service.approve_loan(pk)
            return Response({"status": "approved"}, status=status.HTTP_200_OK)
        except LoanApplicationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Reject a loan application",
        responses={
            200: OpenApiResponse(description="Loan application rejected"),
            400: OpenApiResponse(description="Error rejecting loan application"),
            403: OpenApiResponse(description="Permission denied"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        """
        Admin rejects a loan application.
        """
        loan_service = LoanManagementService()

        if not pk:
            return Response(
                {"error": "Loan ID is required for rejection."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            loan = loan_service.reject_loan(pk)
            return Response({"status": "rejected"}, status=status.HTTP_200_OK)
        except LoanApplicationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Flag a loan application for potential fraud",
        responses={
            201: OpenApiResponse(description="Loan application flagged for fraud"),
            400: OpenApiResponse(description="Error flagging loan application"),
            403: OpenApiResponse(description="Permission denied"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @action(detail=True, methods=["post"], url_path="flag")
    def flag(self, request, pk=None):
        """
        Admin flags a loan application for potential fraud.
        """

        flags = request.data.get("flags", [])
        loan_service = LoanManagementService()

        if not pk:
            return Response(
                {"error": "Loan ID is required for flagging."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            loan = loan_service.flag_loan(pk, flags)
            return Response(
                {
                    "status": "flagged",
                    "loan_id": loan.id,
                    "message": "Application request successfully flagged for fraud.",
                },
                status=status.HTTP_201_CREATED,
            )
        except LoanApplicationError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="View all flagged loan applications",
        responses={
            200: OpenApiResponse(description="List of flagged loans"),
            404: OpenApiResponse(description="No flagged loans found"),
            403: OpenApiResponse(description="Permission denied"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @action(detail=False, methods=["get"], url_path="flagged")
    def flagged_loans(self, request):
        """
        Admin-only endpoint to view all flagged loans
        """
        flagged_loans = LoanApplication.objects.only(
            status=LoanApplication.Status.FLAGGED
        )
        flagged_loans_response = LoanApplicationResponse(flagged_loans, many=True)
        return Response(flagged_loans_response, status.HTTP_200_OK)
