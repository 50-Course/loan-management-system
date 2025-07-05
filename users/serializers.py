from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import BaseUser, Customer, LoanAdmin


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # slap in the user claims (i.e, role)
        token["role"] = user.role
        return token


class AdminUserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = BaseUser
        fields = ("username", "first_name", "last_name", "role", "password")

    def create(self, validated_data):
        role = validated_data.get("role")
        password = validated_data.pop("password")

        if role != BaseUser.RoleType.ADMIN:
            raise serializers.ValidationError(
                {"role": "Only admin users can be created with this serializer."}
            )

        user = LoanAdmin(**validated_data)
        user.set_password(password)
        user.save()
        return user


class CustomerUserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = Customer
        fields = (
            "username",
            "first_name",
            "last_name",
            "role",
            "password",
            "phone_number",
            "date_of_birth",
        )

    def create(self, validated_data):
        role = validated_data.get("role")
        password = validated_data.pop("password")

        if role != BaseUser.RoleType.CUSTOMER:
            # user = LoanAdmin(**validated_data)
            raise serializers.ValidationError(
                {"role": "Only customer users can be created with this serializer."}
            )

        phone_number = validated_data.pop("phone_number", None)
        if not phone_number:
            raise serializers.ValidationError(
                {"phone_number": "Phone number is required for customers."}
            )
        user = Customer(**validated_data)

        user.set_password(password)
        user.save()
        return user
