from rest_framework import serializers

from loans.models import LoanApplication


class LoanApplicationSerializer(serializers.ModelSerializer):
    """
    Serializer for loan applications - used only for admin or internal APIs.
    Converts loan application model instances to JSON format and vice versa.
    """

    class Meta:
        model = LoanApplication
        fields = "__all__"
        exclude = ["id"]


class LoanApplicationRequest(serializers.ModelSerializer):
    """
    Serializer for loan application requests.
    Validates and converts incoming data to a format suitable for creating a loan application.
    """

    # Our Fraud detection syste handles this!
    # def validate_amount_requested(self, value):
    # MAX_LOAN_AMOUNT = 5000000
    # if value > MAX_LOAN_AMOUNT:
    #     raise serializers.ValidationError(
    #         f"Loan amount exceeds the maximum limit of {MAX_LOAN_AMOUNT}."
    #     )
    # return value

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
            "amount_requested": {
                "max_digits": 10,
                "decimal_places": 2,
                "help_text": "Amount needed by the customer for the loan",
            },
            "purpose": {
                # "max_length": 20,
                "choices": LoanApplication.Purpose.choices,
                "help_text": "Purpose of the loan application",
            },
        }


class LoanApplicationResponse(serializers.Serializer):
    """
    Serializer for loan application responses.
    Converts loan application model instances to a simplified JSON format.
    """

    user = serializers.CharField(source="user.get_full_name")
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    purpose = serializers.CharField()
    status = serializers.CharField()
    date_applied = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    date_updated = serializers.DateTimeField(required=False, format="%Y-%m-%d %H:%M:%S")
