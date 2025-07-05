import logging

from drf_spectacular.utils import (OpenApiParameter, OpenApiRequest,
                                   OpenApiResponse, extend_schema,
                                   extend_schema_view)
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from fraud.services import FraudDetectionError
from loans.models import LoanApplication
from loans.serializers import (LoanApplicationResponse,
                               LoanApplicationSerializer)
from loans.services import LoanApplicationError, LoanManagementService
from permissions import IsCustomer, IsLoanAdmin

from .serializers import LoanApplicationRequest

logger = logging.getLogger(__name__)


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
    queryset = LoanApplication.objects.all()

    # overriden this to prevent 'list' and 'create' and every other builtin actions, from appearing
    # ref: https://www.cdrf.co/3.14/rest_framework.viewsets/ModelViewSet.html#get_extra_actions
    @classmethod
    def get_extra_actions(cls):
        """
        Overriding this method allows us to remove unwanted actions
        such as `create` or `list` from the schema.

        Ref: https://www.cdrf.co/3.14/rest_framework.viewsets/ModelViewSet.html#get_extra_actions
        """
        return []

    @extend_schema(
        operation_id="customer_loan_retrieve",
        summary="Retrieve a specific loan application",
        description="Retrieve a specific loan application by ID for the authenticated customer.",
        responses={
            200: OpenApiResponse(
                response=LoanApplicationResponse,
                description="Loan application details",
            ),
            404: OpenApiResponse(description="Loan application not found"),
            403: OpenApiResponse(description="Permission denied"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @action(detail=True, methods=["get"], url_path="loan", url_name="retrieve_loan")
    def retrieve_loan(self, request, *args, **kwargs):
        """
        Retrieve a specific loan application by ID.
        """
        loan_id = kwargs.get("pk")
        if not loan_id:
            return Response(
                {"error": "Loan ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            loan = LoanApplication.objects.get(id=loan_id, user=request.user)
            serializer = LoanApplicationResponse(loan)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LoanApplication.DoesNotExist:
            return Response(
                {"error": "Loan application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @extend_schema(
        operation_id="customer_loan_retrieve",
        summary="View all my loan applications",
        description="Retrieve all loan applications for the authenticated customer.",
        responses={
            200: OpenApiResponse(
                description="List of loan applications",
                response=LoanApplicationResponse,
            ),
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
        description="Submit a new loan application for the authenticated customer.",
        request=OpenApiRequest(request=LoanApplicationRequest),
        responses={
            201: OpenApiResponse(
                description="Loan application created successfully",
                response=LoanApplicationResponse,
            ),
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
            return Response(
                {
                    "message": "Loan application received. Please await approval. Application details",
                    "data": loan_response.data,
                },
                status=status.HTTP_201_CREATED,
            )
        except FraudDetectionError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except LoanApplicationError as err:
            logger.error(f"Loan submission failed for user {user.id}: {str(err)}")
            return Response(
                {"message": "Loan submission failed.", "error": str(err)},
                status=status.HTTP_403_FORBIDDEN
                if "Only customers can submit loans" in str(err)
                else status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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
    serializer_class = LoanApplicationSerializer
    queryset = LoanApplication.objects.all()

    @classmethod
    def get_extra_actions(cls):
        """
        Overriding this method allows us to remove unwanted actions
        such as `create` or `list` from the schema.

        Ref: https://www.cdrf.co/3.14/rest_framework.viewsets/ModelViewSet.html#get_extra_actions
        """
        return []

    @extend_schema(
        operation_id="admin_loan_retrieve",
        summary="Retrieve a specific loan application - Admin Only",
        description="Admin can view details of a specific loan application by ID",
        responses={
            200: OpenApiResponse(
                response=LoanApplicationSerializer,
                description="Loan application details",
            ),
            403: OpenApiResponse(description="Permission denied"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @action(
        detail=True, methods=["get"], url_path="loan", url_name="retrieve_customer_loan"
    )
    def retrieve_customer_loan(self, request, pk=None):
        """
        Admin views a specific loan application by ID.
        """
        loan = get_object_or_404(LoanApplication, pk)
        serializer = LoanApplicationSerializer(loan)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="admin_all_loans",
        summary="Retrieve all loan applications - Admin Only",
        description="Admin can view all loan applications",
        responses={
            200: OpenApiResponse(
                description="List of all loan applications",
                response=LoanApplicationSerializer,
            ),
            404: OpenApiResponse(description="No loan applications found"),
            403: OpenApiResponse(description="Permission denied"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @action(detail=False, methods=["get"])
    def all_loans(self, request):
        """
        Admin can view all loan applications.
        """
        loans = LoanApplication.objects.all()
        serializer = LoanApplicationSerializer(loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="admin_loan_approve",
        summary="Approve a loan application - Admin Only",
        description="Approve a loan application",
        responses={
            200: OpenApiResponse(description="Loan application approved"),
            400: OpenApiResponse(description="Error approving loan application"),
            403: OpenApiResponse(description="Permission denied"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @action(detail=True, methods=["post"], url_path="approve")
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
        summary="Reject a loan application - Admin Only",
        description="Reject a loan application by ID",
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
        summary="Flag a loan application for potential fraud - Admin Only",
        description="Admin flags a loan application for potential fraud",
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
        summary="View all flagged loan applications - Admin Only",
        description="Admin can view all flagged loan applications",
        responses={
            200: OpenApiResponse(
                description="List of flagged loans", response=LoanApplicationResponse
            ),
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
        flagged_loans = LoanApplication.objects.filter(
            status=LoanApplication.Status.FLAGGED
        )
        flagged_loans_response = LoanApplicationResponse(flagged_loans, many=True)
        return Response(flagged_loans_response, status.HTTP_200_OK)
