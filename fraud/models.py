from django.db import models


class FraudFlag(models.Model):
    """
    Flag for potential fraud in a transaction.
    """

    from loans.models import LoanApplication

    loan_application = models.ForeignKey(
        LoanApplication, on_delete=models.CASCADE, related_name="fraud_flags"
    )
    reason = models.TextField(
        help_text="Reason for flagging the transaction as potential fraud."
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
