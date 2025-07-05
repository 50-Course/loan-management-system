from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from users.models import Customer, LoanAdmin

from .serializers import (CustomTokenObtainPairSerializer,
                          UserRegistrationResponseSerializer,
                          UserRegistrationSerializer)


@extend_schema(
    tags=["Users"],
    operation_id="authenticate_user",
    summary="Login User",
    description="Authenticate user and return JWT token.",
    request=CustomTokenObtainPairSerializer,
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            description="User authenticated successfully.",
            response=CustomTokenObtainPairSerializer,
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            description="Invalid credentials."
        ),
        status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
            description="Server error occurred."
        ),
    },
)
class UserLoginView(TokenObtainPairView):
    """
    User login for token authentication.
    """

    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(
    tags=["Users"],
    operation_id="register_user",
    summary="Register User",
    description="Register a new user on the platform - either as a Customer or an Admin.",
    request=UserRegistrationSerializer,
    responses={
        status.HTTP_201_CREATED: OpenApiResponse(
            description="User registered successfully.",
            response=UserRegistrationResponseSerializer,
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            description="Invalid registration data.",
        ),
        status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
            description="Server error occurred.",
        ),
    },
)
class UserRegisterView(APIView):
    """
    Register new user (Customer or Admin).
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        response_serializer = UserRegistrationResponseSerializer(user)

        response_data = {
            "message": "User registered successfully. Please log in to continue.",
            "data": response_serializer.data,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
