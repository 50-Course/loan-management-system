from rest_framework import serializers

from fraud.models import FraudFlag
from loans.models import LoanApplication
from users.models import Customer


class ErrorResponseSerializer(serializers.Serializer):
    """
    Serializer for error responses.
    Used to standardize error messages across the API.
    """

    status = serializers.CharField(
        help_text="Short description status of the operation, typically 'error', 'flagged' or 'fail'.",
    )
    error = serializers.CharField(
        help_text="Error message describing the issue with the request."
    )
    code = serializers.IntegerField(
        help_text="HTTP status code representing the error type.",
        required=False,
        default=400,
    )
    detail = serializers.JSONField(
        help_text="Detailed description of the error, if available.",
        required=False,
    )


class UserSummarySerializer(serializers.ModelSerializer):
    # Serializer for user summary - used in admin or internal APIs.
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.CharField(
        source="customer.phone_number", read_only=True, default=""
    )

    class Meta:
        model = Customer
        fields = ["id", "full_name", "email", "phone_number"]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class MyLoanApplicationSerializer(serializers.ModelSerializer):
    # Designed for users to view their own loan applications
    class Meta:
        model = LoanApplication
        exclude = [
            "id",
            "user",
            "date_updated",  # Exclude date_updated for user view - that's not needed
            # "purpose",  # Exclude purpose for user view - not needed, well not sure, but we let's roll with it
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # convert timezone-aware datetime to string
        data["date_applied"] = instance.date_applied.strftime("%Y-%m-%d %H:%M:%S")
        return data


class FlagLoanRequest(serializers.Serializer):
    # Serializer for flagging a loan application in the admin panel
    reason = serializers.ChoiceField(
        choices=FraudFlag.Reason.choices,
        help_text="Reason for flagging the loan application as potential fraud.",
    )
    comments = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Additional comments or notes regarding the fraud flag.",
    )


class FlagLoanResponse(serializers.Serializer):
    # Serializer for the response after flagging a loan application
    message = serializers.CharField(
        help_text="Confirmation message after flagging the loan application."
    )
    fraud_flag_id = serializers.IntegerField(help_text="ID of the created fraud flag.")


class FlaggedLoanSerializer(serializers.ModelSerializer):
    # Displays flagged loans for admin view
    user_profile = UserSummarySerializer(source="user", read_only=True)
    loan_id = serializers.IntegerField(source="id", read_only=True)
    fraud_flags = serializers.SerializerMethodField(
        help_text="List of reasons for flagging the loan application as potential fraud.",
    )
    comments = serializers.CharField()

    def get_fraud_flags(self, obj) -> list:
        return [flag.reason for flag in obj.fraud_flags.value_list("reason", flat=True)]

    class Meta:
        model = LoanApplication
        fields = [
            "user_profile",
            "loan_id",
            "fraud_flags",
            "comments",
        ]


class AdminViewLoanApplicationSerializer(serializers.ModelSerializer):
    # Serializes loan applications for admin view - works best for many loan applications.
    user_profile = UserSummarySerializer(source="user", read_only=True)
    loan_id = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = LoanApplication
        fields = [
            "loan_id",
            "user_profile",
            "amount_requested",
            "purpose",
            "status",
            "date_applied",
            "date_updated",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # convet timezone-aware datetime to string
        data["date_applied"] = instance.date_applied.strftime("%Y-%m-%d %H:%M:%S")
        if instance.date_updated:
            data["date_updated"] = instance.date_updated.strftime("%Y-%m-%d %H:%M:%S")
        else:
            data["date_updated"] = None
        return data


class LoanApplicationRequest(serializers.ModelSerializer):
    """
    Serializer for loan application requests.
    Validates and converts incoming data to a format suitable for creating a loan application.
    """

    class Meta:
        model = LoanApplication
        fields = [
            "user",
            "amount_requested",
            "purpose",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "user": {"read_only": True},
        }


class LoanApplicationResponse(serializers.Serializer):
    """
    Serializer for loan application responses.
    Converts loan application model instances to a simplified JSON format.
    """

    full_name = serializers.CharField(source="user.get_full_name")
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, source="amount_requested"
    )
    purpose = serializers.CharField()
    status = serializers.CharField()
    date_applied = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    date_updated = serializers.DateTimeField(required=False, format="%Y-%m-%d %H:%M:%S")
