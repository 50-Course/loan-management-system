from django.db import models


class FraudFlag(models.Model):
    """
    Flag for potential fraud in a transaction.
    """

    class Reason(models.TextChoices):
        # Reasons for flagging a loan application
        SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY", "Suspicious Activity"
        INCOMPLETE_KYC = "INCOMPLETE_KYC", "Incomplete KYC"
        INCONSISTENT_INFORMATION = (
            "INCONSISTENT_INFORMATION",
            "Inconsistent Information",
        )
        HIGH_RISK_PROFILE = "HIGH_RISK_PROFILE", "High Risk Profile"
        UNUSUAL_TRANSACTION = "UNUSUAL_TRANSACTION", "Unusual Transaction"

        INACTIVE_DEBIT_CARD = (
            "INACTIVE_DEBIT_CARD",
            "Inactive Debit Card",
        )  # simlating the QC app
        DIRECT_DEBIT_FAILURE = (
            "DIRECT_DEBIT_FAILURE",
            "Direct Debit Failure",
        )  # the 50 naira test for auto-loan recovery
        OTHER = "OTHER", "Other"

    from loans.models import LoanApplication

    loan_application = models.ForeignKey(
        LoanApplication, on_delete=models.CASCADE, related_name="fraud_flags"
    )
    reason = models.CharField(
        help_text="Reason for flagging the transaction as potential fraud.",
        max_length=50,
        choices=Reason.choices,
    )
    resolved = models.BooleanField(
        default=False, help_text="Indicates whether the fraud flag has been resolved."
    )
    comments = models.TextField(
        blank=True,
        help_text="Additional comments or notes regarding the fraud flag.",
    )

    def __str__(self):
        return f"Flagged for {self.loan_application.user} - {str(self.reason)[:50]}"

    # class Meta:
    #     ordering = ["-loan_application__date_applied"]
