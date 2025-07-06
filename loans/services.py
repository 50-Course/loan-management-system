from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from loans.models import LoanApplication
from users.models import BaseUser, Customer


class LoanApplicationError(Exception):
    """Base class for loan application errors."""

    pass


def check_eligibility(customer: "Customer") -> bool:
    """
    Check if the user is eligible for a loan.

    Prevent users from submitting multiple loan applications within 24 hours.
    """
    if customer.flagged_for_fraud:
        raise LoanApplicationError("User is flagged for fraud.")

    last_24_hours = timezone.now() - timedelta(hours=24)
    recent_loan = (
        LoanApplication.objects.filter(
            user=customer,
            date_applied__gte=last_24_hours,
        )
        .order_by("-date_applied")
        .first()
    )

    if recent_loan:
        raise LoanApplicationError(
            "You cannot submit another loan application within 24 hours of your last one."
        )

    return True


@transaction.atomic
def submit_loan(user: "BaseUser", amount: Decimal, purpose: str) -> "LoanApplication":
    from fraud.services import FraudDetectionError, FraudDetectionService

    fraud_detection_service = FraudDetectionService()

    if not hasattr(user, "customer"):
        raise LoanApplicationError("Only customers can submit loan applications.")

    customer = user.customer
    check_eligibility(customer)

    # we are not using .create method because that would save our application
    # directly to the database, in-memory route is the way to go here so we can run our checks
    loan = LoanApplication(user=customer, amount_requested=amount, purpose=purpose)
    fraud_check_result = fraud_detection_service.run_fraud_checks(loan)

    if fraud_check_result["status"] == "fraudlent":
        raise LoanApplicationError(
            f"Loan is flagged for fraud due to: {', '.join(fraud_check_result['flags'])}"
        )

    loan.save()
    return loan


class LoanManagementService:
    """
    Handles the management of loan applications, including approval and rejection.

    This service is used my LoanAdmins to manage loan applications.
    """

    def approve_loan(self, loan: "LoanApplication") -> "LoanApplication":
        """
        Approve a loan application if it's not flagged for fraud.
        """
        from fraud.services import FraudDetectionError, FraudDetectionService

        fraud_check = FraudDetectionService()

        if loan.status != LoanApplication.Status.PENDING:
            raise LoanApplicationError("Loan application is not in a pending state.")

        if loan.status == LoanApplication.Status.FLAGGED:
            raise LoanApplicationError("Cannot approve a flagged loan.")

        # Perform fraud checks - here we only care for partial checks
        # becuase this action is performed by admin only
        if fraud_check.is_fraudulent(loan):
            raise FraudDetectionError("Loan is flagged as fraudulent.")

        loan.status = LoanApplication.Status.APPROVED
        loan.save()
        return loan

    def reject_loan(self, loan: "LoanApplication"):
        """Reject loan due to fraud suspicion."""
        if loan.status == LoanApplication.Status.APPROVED:
            raise LoanApplicationError("Cannot reject an approved loan.")

        if loan.status == LoanApplication.Status.REJECTED:
            raise LoanApplicationError("Loan application has already been rejected.")

        loan.status = LoanApplication.Status.REJECTED
        loan.save()
        return loan

    def flag_loan(self, loan: "LoanApplication", flags: list) -> "LoanApplication":
        """
        Flag a loan as potentially fraudulent - Admin action.
        """
        from fraud.services import AuditService, FraudDetectionService

        if loan.status != LoanApplication.Status.PENDING:
            raise LoanApplicationError("Loan application is not in a pending state.")

        fraud_detection_service = FraudDetectionService()
        fraud_detection_service.flag_loan(loan, flags)

        return loan
