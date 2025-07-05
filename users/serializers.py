from rest_framework import serializers
from rest_framework.serializers import Serializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import BaseUser, Customer, LoanAdmin


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # slap in the user claims (i.e, role)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data.update(
            {
                "username": self.user.username,
                "role": self.user.role,
            }
        )
        return {"message": "Login successful", "data": data}


class APIResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    role = serializers.ChoiceField(choices=BaseUser.RoleType.choices, required=True)

    class Meta:
        model = BaseUser
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "password",
            "phone_number",
            "date_of_birth",
        )
        extra_kwargs = {
            "email": {"required": True, "allow_blank": False},
            "phone_number": {"required": False},
            "date_of_birth": {"required": False},
        }

    def validate(self, attrs):
        role = attrs.get("role")
        if role == BaseUser.RoleType.ADMIN and "phone_number" in attrs:
            raise serializers.ValidationError(
                {"phone_number": "Phone number is not allowed for admins."}
            )
        if role == BaseUser.RoleType.CUSTOMER and "date_of_birth" not in attrs:
            raise serializers.ValidationError(
                {"date_of_birth": "Date of birth is required for customers."}
            )
        if role == BaseUser.RoleType.CUSTOMER and "phone_number" not in attrs:
            raise serializers.ValidationError(
                {"phone_number": "Phone number is required for customers."}
            )
        return attrs

    def create(self, validated_data):
        role = validated_data.get("role")
        password = validated_data.pop("password")
        phone_number = validated_data.get("phone_number", None)
        date_of_birth = validated_data.get("date_of_birth", None)

        if role == BaseUser.RoleType.ADMIN:
            user = LoanAdmin(**validated_data)
        elif role == BaseUser.RoleType.CUSTOMER:
            if not phone_number:
                raise serializers.ValidationError(
                    {"phone_number": "Phone number is required for customers."}
                )
            if not date_of_birth:
                raise serializers.ValidationError(
                    {"date_of_birth": "Date of birth is required for customers."}
                )

            user = Customer(**validated_data)
        else:
            raise serializers.ValidationError(
                {"role": "Role must be either 'ADMIN' or 'CUSTOMER'."}
            )

        user.set_password(password)
        user.save()
        return user


class UserRegistrationResponseSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        return f"{obj.get_full_name()}"

    class Meta:
        model = BaseUser
        fields = ("full_name", "username", "role")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["message"] = "User registered successfully"
        return representation
