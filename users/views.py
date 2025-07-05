from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from users.models import Customer, LoanAdmin

from .serializers import (AdminUserRegistrationSerializer,
                          CustomerUserRegistrationSerializer,
                          CustomTokenObtainPairSerializer)


@extend_schema(tags=["Users"])
class UserLoginView(TokenObtainPairView):
    """
    User login for token authentication.
    """

    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(tags=["Users"])
class UserRegisterView(generics.CreateAPIView):
    """
    Register new user (Customer or Admin).
    """

    def get_serializer_class(self):
        role = self.request.data.get("role")

        if role == "ADMIN":
            return AdminUserRegistrationSerializer
        elif role == "CUSTOMER":
            return CustomerUserRegistrationSerializer
        else:
            raise serializers.ValidationError(
                {"role": "Role must be either 'ADMIN' or 'CUSTOMER'."}
            )
