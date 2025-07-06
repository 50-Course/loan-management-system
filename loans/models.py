from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class LoanApplication(models.Model):
    """
    Represents an loan application
    """

    from users.models import Customer

    class Status(models.TextChoices):
        # Status choices for a loan application
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        FLAGGED = "FLAGGED", "Flagged for Fraud"

    class Purpose(models.TextChoices):
        # Purpose choices for a loan application
        PERSONAL = "PERSONAL", "Personal"
        BUSINESS = "BUSINESS", "Business"
        EDUCATION = "EDUCATION", "Education"
        MEDICAL = "MEDICAL", "Medical"
        OTHER = "OTHER", "Other"

    user = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="loan_applications",
        related_query_name="loan_application",
        help_text="Customer applying for the loan",
    )
    amount_requested = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount needed by the customer for the loan",
        validators=[
            MinValueValidator(Decimal("1000.00")),
            MaxValueValidator(Decimal("5_000_000.00")),
        ],
    )
    purpose = models.CharField(
        max_length=20,
        choices=Purpose.choices,
        help_text="Purpose of the loan application",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Current status of the loan application",
    )
    date_applied = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the loan application was submitted",
    )
    date_updated = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the loan application was last updated",
    )

    def __str__(self):
        return f"{self.user} - {self.amount_requested} - {self.status}"

    def flag_as_fraud(self, reason: str, comments: str = "") -> None:
        """
        Flag the loan application as fraudulent with a reason and optional comments.
        """
        from fraud.models import FraudFlag

        if not reason:
            raise ValueError("Reason for flagging must be provided.")

        fraud_flag = FraudFlag.objects.create(
            loan_application=self,
            reason=reason,
            comments=comments,
        )
        return fraud_flag

    def is_high_risk(self) -> bool:
        """
        Check if a loan has a high risk based on certain conditions, which could include the loan amount or other factors.

        Why you go dey find 1 grand loan if your earning power never touch base?
        """
        return self.amount_requested > 1_000_000 and self.user.date_of_birth.year < 2000

    class Meta:
        ordering = ["-date_applied"]
        verbose_name = "Loan"
        verbose_name_plural = "Loans"
