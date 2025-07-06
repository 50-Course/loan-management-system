import logging

from django.utils.html import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
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
from loans.filters import LoanApplicationFilter
from loans.models import LoanApplication
from loans.serializers import (AdminViewLoanApplicationSerializer,
                               LoanApplicationResponse,
                               MyLoanApplicationSerializer)
from loans.services import LoanApplicationError, LoanManagementService
from permissions import IsCustomer, IsLoanAdmin

from .serializers import (ErrorResponseSerializer, FlaggedLoanSerializer,
                          FlagLoanRequest, FlagLoanResponse,
                          LoanApplicationRequest)

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
            404: OpenApiResponse(
                ErrorResponseSerializer, description="Loan application not found"
            ),
            403: OpenApiResponse(
                ErrorResponseSerializer, description="Permission denied"
            ),
            500: OpenApiResponse(
                ErrorResponseSerializer, description="Internal server error"
            ),
        },
    )
    @action(detail=True, methods=["get"], url_path="loan", url_name="retrieve_loan")
    def retrieve_loan(self, request, *args, **kwargs):
        """
        Retrieve a specific loan application by ID.
        """
        loan_id = kwargs.get("id")
        if not loan_id:
            return Response(
                ErrorResponseSerializer(
                    {
                        "status": "error",
                        "error": "Loan ID is required",
                        "code": 400,
                    }
                ).data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            loan = LoanApplication.objects.get(id=loan_id, user=request.user)
            serializer = LoanApplicationResponse(loan)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LoanApplication.DoesNotExist:
            return Response(
                ErrorResponseSerializer(
                    {
                        "status": "error",
                        "error": "Loan application not found",
                        "code": 404,
                    }
                ).data,
                status=status.HTTP_404_NOT_FOUND,
            )

    @extend_schema(
        operation_id="customer_loan_retrieve",
        summary="View my loan applications",
        description="Retrieve all loan applications for the authenticated customer.",
        responses={
            200: OpenApiResponse(
                description="List of loan applications",
                response=MyLoanApplicationSerializer(many=True),
            ),
            404: OpenApiResponse(
                ErrorResponseSerializer, description="Loan application not found"
            ),
            403: OpenApiResponse(
                ErrorResponseSerializer, description="Permission denied"
            ),
            500: OpenApiResponse(
                ErrorResponseSerializer, description="Internal server error"
            ),
        },
    )
    @action(detail=False, methods=["get"], url_path="requests", url_name="my_loans")
    def my_applications(self, request):
        """
        Retrieve all loan applications for the authenticated user.
        """
        try:
            loans = LoanApplication.objects.filter(user=request.user)
            serializer = MyLoanApplicationSerializer(loans, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving loan applications: {str(e)}")
            return Response(
                ErrorResponseSerializer(
                    {"status": "error", "error": str(e), "code": 500}
                ).data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Apply for a loan",
        description="Submit a new loan application for the authenticated customer.",
        request=OpenApiRequest(request=LoanApplicationRequest),
        responses={
            201: OpenApiResponse(
                description="Loan application created successfully",
                response=LoanApplicationResponse,
            ),
            400: OpenApiResponse(
                ErrorResponseSerializer, description="Invalid request data"
            ),
            403: OpenApiResponse(
                ErrorResponseSerializer, description="Permission denied"
            ),
            500: OpenApiResponse(
                ErrorResponseSerializer, description="Internal server error"
            ),
        },
    )
    @action(detail=False, methods="post", url_path="loan", url_name="submit_loan")
    def submit(self, request, *args, **kwargs):
        """
        Submit a new application

        Validates the request data and creates a new loan application for the authenticated user.
        """
        from loans import services as loan_service

        serializer = LoanApplicationRequest(data=request.data)
        serializer.is_valid(raise_exception=True)

        loan_data = serializer.validated_data
        try:
            loan = loan_service.submit_loan(
                user=request.user,  # type: ignore[assignment]
                amount=loan_data["amount_requested"],  # type: ignore[assignment]
                purpose=loan_data["purpose"],  # type: ignore[assignment]
            )
            loan_response = LoanApplicationResponse(loan)
            return Response(
                {
                    "message": "Loan application received. Please await approval. Application details",
                    "data": loan_response.data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as err:
            logger.error(f"Validation error during loan submission: {str(err)}")
            return Response(
                ErrorResponseSerializer(
                    {
                        "status": "fail",
                        "error": "Invalid data submitted.",
                        "code": 400,
                        "detail": str(err.detail),
                    }
                ).data,
                status=status.HTTP_400_BAD_REQUEST,
            )
        except FraudDetectionError as err:
            logger.warning(f"Loan application flagged for fraud: {str(err)}")
            return Response(
                ErrorResponseSerializer(
                    {"status": "flagged", "error": str(err), "code": 400}
                ).data,
                status=status.HTTP_400_BAD_REQUEST,
            )
        except LoanApplicationError as err:
            logger.error(
                f"Loan submission failed for user {request.user.id}: {str(err)}"
            )
            status_code = 400 if "24 hours" in str(err).lower() else 403
            return Response(
                ErrorResponseSerializer(
                    {"status": "error", "error": str(err), "code": status_code}
                ).data,
                status=status_code,
            )
        except PermissionDenied as err:
            logger.error(f"Permission denied for user {request.user.id}: {str(err)}")
            return Response(
                ErrorResponseSerializer(
                    {"status": "permission_denied", "error": str(err), "code": 403}
                ).data,
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as e:
            logger.error(f"Unexpected error during loan submission: {str(e)}")
            return Response(
                ErrorResponseSerializer(
                    {"status": "fail", "error": str(e), "code": 500}
                ).data,
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
    queryset = LoanApplication.objects.select_related("user").all()

    filter_backends = [DjangoFilterBackend]
    filterset_class = LoanApplicationFilter

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
        summary="Get a specific loan application -  Admin Only",
        description="Retrieve detailed information of a specific loan application using its ID",
        responses={
            200: OpenApiResponse(
                response=AdminViewLoanApplicationSerializer,
                description="Loan application details",
            ),
            403: OpenApiResponse(
                ErrorResponseSerializer, description="Permission denied"
            ),
            500: OpenApiResponse(
                ErrorResponseSerializer, description="Internal server error"
            ),
        },
    )
    @action(
        detail=True, methods=["get"], url_path="loan", url_name="retrieve_customer_loan"
    )
    def retrieve_customer_loan(self, request, id=None):
        """
        Admin views a specific loan application by ID.
        """
        try:
            loan = LoanApplication.objects.get(id=id)
            serializer = AdminViewLoanApplicationSerializer(loan)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LoanApplication.DoesNotExist:
            return Response(
                ErrorResponseSerializer(
                    {
                        "status": "error",
                        "error": "Loan Application not found",
                        "code": 404,
                    }
                ).data,
                status=status.HTTP_404_NOT_FOUND,
            )

    @extend_schema(
        operation_id="admin_all_loans",
        summary="Get all loan applications -  Admin Only",
        description="Retrieve all loan applications. Supports filters like status, user_email, date range.",
        responses={
            200: OpenApiResponse(
                description="List of all loan applications",
                response=AdminViewLoanApplicationSerializer(many=True),
            ),
            403: OpenApiResponse(
                ErrorResponseSerializer, description="Permission denied"
            ),
            500: OpenApiResponse(
                ErrorResponseSerializer, description="Internal server error"
            ),
        },
    )
    @action(detail=False, methods=["get"], url_name="all_loans")
    def all_loans(self, request):
        """
        Admin can view all loan applications.
        """
        try:
            loans = LoanApplication.objects.all()
            serializer = AdminViewLoanApplicationSerializer(loans, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except PermissionDenied as e:
            logger.error(f"Permission denied for admin: {str(e)}")
            return Response(
                ErrorResponseSerializer(
                    {"status": "permission_denied", "error": str(e), "code": 403}
                ).data,
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as e:
            logger.error(f"Error retrieving all loans: {str(e)}")
            return Response(
                ErrorResponseSerializer(
                    {"status": "error", "error": str(e), "code": 500}
                ).data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        operation_id="admin_loan_approve",
        summary="Approve a loan - Admin Only",
        description="Approve a customer's loan application",
        responses={
            200: OpenApiResponse(description="Loan Approved"),
            400: OpenApiResponse(
                ErrorResponseSerializer, description="Error approving loan application"
            ),
            403: OpenApiResponse(
                ErrorResponseSerializer, description="Permission denied"
            ),
            500: OpenApiResponse(
                ErrorResponseSerializer, description="Internal server error"
            ),
        },
    )
    @action(detail=True, methods=["post"], url_path="approve", url_name="approve_loan")
    def approve(self, request, id=None):
        """
        Admin approves a loan application.
        """
        if not id:
            return Response(
                {"error": "Loan ID is required for approval."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        loan_service = LoanManagementService()
        try:
            loan_obj = LoanApplication.objects.get(id=id)
            loan = loan_service.approve_loan(loan_obj)
            loan_data = LoanApplicationResponse(loan).data
            return Response(
                {
                    "status": "approved",
                    "loan_details": loan_data,
                },
                status=status.HTTP_200_OK,
            )
        except LoanApplication.DoesNotExist:
            return Response(
                ErrorResponseSerializer(
                    {
                        "status": "error",
                        "error": "Loan application not found",
                        "code": 404,
                    }
                ).data,
                status=status.HTTP_404_NOT_FOUND,
            )
        except LoanApplicationError as e:
            logger.error(f"Error approving loan {id}: {str(e)}")
            return Response(
                ErrorResponseSerializer(
                    {"status": "error", "error": str(e), "code": 400}
                ).data,
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="Reject a loan - Admin Only",
        description="Reject a loan application and provide reason if applicable",
        responses={
            200: OpenApiResponse(description="Loan rejected"),
            403: OpenApiResponse(
                ErrorResponseSerializer, description="Permission denied"
            ),
            500: OpenApiResponse(
                ErrorResponseSerializer, description="Internal server error"
            ),
        },
    )
    @action(detail=True, methods=["post"], url_path="reject", url_name="reject_loan")
    def reject(self, request, id=None):
        """
        Admin rejects a loan application.
        """
        loan_service = LoanManagementService()

        if not id:
            return Response(
                {"error": "Loan ID is required for rejection."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            loan_obj = LoanApplication.objects.get(id=id)
            loan = loan_service.reject_loan(loan_obj)
            loan_data = LoanApplicationResponse(loan).data
            return Response(
                {
                    "status": "rejected",
                    "loan_details": loan_data,
                },
                status=status.HTTP_200_OK,
            )
        except LoanApplication.DoesNotExist:
            logger.error(f"Loan application {id} not found for rejection")
            return Response(
                ErrorResponseSerializer(
                    {
                        "status": "error",
                        "error": "Loan application not found",
                        "code": 404,
                    }
                ).data,
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDenied as e:
            logger.error(f"Permission denied for rejecting loan {id}: {str(e)}")
            return Response(
                ErrorResponseSerializer(
                    {
                        "status": "permission_denied",
                        "error": "Only loan administrators are authorized to perform this operation",
                        "code": 403,
                        "detail": str(e),
                    }
                ).data,
                status=status.HTTP_403_FORBIDDEN,
            )
        except LoanApplicationError as e:
            logger.error(f"Error rejecting loan {id}: {str(e)}")
            return Response(
                ErrorResponseSerializer(
                    {"status": "error", "error": str(e), "code": 400}
                ).data,
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="Flag Loan - Admin Only",
        description="Mark a loan as suspicious (potential fraud) for manual review",
        request=OpenApiRequest(request=FlagLoanRequest(many=True)),
        responses={
            200: OpenApiResponse(
                FlagLoanResponse, description="Loan application flagged for fraud"
            ),
            400: OpenApiResponse(
                ErrorResponseSerializer, description="Error flagging loan application"
            ),
            403: OpenApiResponse(
                ErrorResponseSerializer, description="Permission denied"
            ),
            500: OpenApiResponse(
                ErrorResponseSerializer, description="Internal server error"
            ),
        },
    )
    @action(detail=True, methods=["post"], url_path="flag", url_name="flag_loan")
    def flag(self, request, id=None):
        """
        Admin flags a loan application for potential fraud.
        Accepts a list of fraud reasons and comments.
        """

        serializer = FlagLoanRequest(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        validated_flags = serializer.validated_data

        loan_service = LoanManagementService()

        if not id:
            return Response(
                {"error": "Loan ID is required for flagging."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            loan_obj = LoanApplication.objects.get(id=id)
            loan = loan_service.flag_loan(loan_obj, validated_flags)  # type: ignore
            return Response(
                {
                    "status": "flagged",
                    "loan_id": loan.id,
                    "message": "Application flagged for fraud",
                    "flags": serializer.validated_data,
                },
                status=status.HTTP_200_OK,
            )
        except LoanApplication.DoesNotExist:
            return Response(
                ErrorResponseSerializer(
                    {
                        "status": "error",
                        "error": "Loan application not found",
                        "code": 404,
                    }
                ).data,
                status=status.HTTP_404_NOT_FOUND,
            )
        except LoanApplicationError as err:
            return Response(
                ErrorResponseSerializer({"status": "error", "error": str(err)}).data,
                status=status.HTTP_400_BAD_REQUEST,
            )
        except PermissionDenied as err:
            return Response(
                ErrorResponseSerializer(
                    {
                        "status": "permission_denied",
                        "error": "Only loan administrators are authorized to perform this operation",
                        "code": 403,
                        "detail": str(err),
                    },
                ).data,
                status=status.HTTP_403_FORBIDDEN,
            )

    @extend_schema(
        summary="Get all flagged loans - Admin Only",
        description="Retrieve all loans flagged for fraud review",
        responses={
            200: OpenApiResponse(
                description="List of flagged loans",
                response=FlaggedLoanSerializer(many=True),
            ),
            404: OpenApiResponse(description="No flagged loans found"),
            403: OpenApiResponse(
                ErrorResponseSerializer, description="Permission denied"
            ),
            500: OpenApiResponse(
                ErrorResponseSerializer, description="Internal server error"
            ),
        },
    )
    @action(detail=False, methods=["get"], url_path="flagged", url_name="flagged_loans")
    def flagged_loans(self, request):
        """
        Admin-only endpoint to view all flagged loans
        """
        try:
            flagged_loans = LoanApplication.objects.filter(
                status=LoanApplication.Status.FLAGGED
            )
            flagged_loans_data = FlaggedLoanSerializer(flagged_loans, many=True).data
            return Response(flagged_loans_data, status.HTTP_200_OK)
        except PermissionDenied as e:
            logger.error(f"Permission denied for retrieving flagged loans: {str(e)}")
            return Response(
                ErrorResponseSerializer(
                    {
                        "status": "permission_denied",
                        "error": "Only loan administrators is authorized to perform this operation",
                        "code": 403,
                        "detail": str(e),
                    },
                ).data,
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as e:
            logger.error(f"Error retrieving flagged loans: {str(e)}")
            return Response(
                ErrorResponseSerializer(
                    {"status": "error", "error": str(e), "code": 500}
                ).data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
