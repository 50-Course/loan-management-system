"""
Fraud Detection Service Unit (FDU)
"""

import logging
from datetime import timedelta
from typing import Literal

from django.db.models import Q
from django.utils import timezone

from fraud.constants import CLEAN, FRAUD
from fraud.models import FraudFlag
from loans.models import LoanApplication
from loans.services import LoanApplicationError
from users.models import Customer, LoanAdmin

logger = logging.getLogger(__name__)


class FraudDetectionError(Exception):
    pass


class FraudDetectionService:
    """
    BeeKeeper is a service that manages the beehive and ensures the bees are healthy.

    BeeKeeper is our Fraud Detection Service, which monitors user activities, patterns,
    and flags suspicious behavior to prevent fraud.
    """

    MAX_LOAN_AMOUNT = 5_000_000

    def fraudlent_users(self) -> list:
        """
        Returns a list of users flagged for fraudulent activities.
        """
        fraudlent_users = Customer.objects.filter(flagged_for_fraud=True).values(
            "first_name", "last_name", "phone_number", "email"
        )
        return list(fraudlent_users)

    def fraudlent_loans(self) -> list:
        """
        Returns a list of loans flagged for fraudulent activities.
        """
        fraudulent_loans = LoanApplication.objects.filter(
            status=LoanApplication.Status.FLAGGED
        ).values(
            "id",
            "user__first_name",
            "user__last_name",
            "amount_requested",
            "date_applied",
        )
        return list(fraudulent_loans)

    def flag_loan(self, loan: "LoanApplication", flags: list) -> None:
        """
        Automatically flag a loan as fraudulent.
        """

        if not flags:
            raise ValueError("At least one flag must be provided.")

        # Check if the loan is already flagged
        if loan.status == LoanApplication.Status.FLAGGED:
            raise FraudDetectionError("Loan application is already flagged for fraud.")

        # Check if the loan is fraudulent
        if not self.is_fraudulent(loan):
            raise FraudDetectionError("Loan application does not meet fraud criteria.")

        loan.status = LoanApplication.Status.FLAGGED
        loan.save()

        for entry in flags:
            if isinstance(entry, dict):
                reason = entry.get("reason")
                comments = entry.get("comments", "")
            elif isinstance(entry, FraudFlag.Reason):
                reason = entry.value
                comments = ""
            else:
                raise ValueError(f"Unsupported flag entry: {entry}")

            loan.flag_as_fraud(reason=reason, comments=comments)

        AuditService.log_activity(f"Loan {loan.id} flagged for fraud: {flags}")
        admins = LoanAdmin.objects.values_list("email", flat=True)
        if len(admins) > 0:
            AuditService.alert(
                list(admins),
                message=f"[FRAUD ALERT!] Loan {loan.id} flagged for fraud. ",
            )

    def suspicious_email_domain(self, user: Customer) -> bool:
        """
        Check if the email domain is used by more than 10 different users.
        """
        domain = user.email.split("@")[-1]
        return Customer.objects.filter(email__endswith=domain).count() > 10

    def too_many_applications(self, user: Customer) -> bool:
        """
        Check if the user has submitted more than 3 applications in the last 24 hours.
        """
        threshold = 3
        now = timezone.now()

        recent_loans = LoanApplication.objects.filter(
            user=user, date_applied__gte=now - timedelta(hours=24)
        )
        return recent_loans.count() > threshold

    def duplicate_account(self, user: "Customer") -> bool:
        """
        Check if the user has multiple accounts with profile information that matches.

        here, we consider if we have any of the following matches:
        - first name, last name, date of birth (if available), phone number (if available)
        """

        query = Q()

        if user.email:
            query |= Q(email=user.email)

        if user.first_name:
            query |= Q(first_name=user.first_name)  # type: ignore

        if user.last_name:
            query |= Q(last_name=user.last_name)  # type: ignore

        if user.date_of_birth:
            query |= Q(date_of_birth=user.date_of_birth)  # type: ignore

        if hasattr(user, "phone_number") and user.phone_number:
            query |= Q(phone_number=user.phone_number)  # type: ignore

        return Customer.objects.filter(query).exclude(id=user.id).exists()

    def _amount_exceeds_limit(self, loan_application: "LoanApplication") -> bool:
        """
        Check if the loan amount exceeds the maximum limit.
        """
        return loan_application.amount_requested > self.MAX_LOAN_AMOUNT

    def is_fraudulent(self, loan: "LoanApplication") -> bool:
        """
        Check if the loan application is fraudulent based on various criteria.
        """
        return self._amount_exceeds_limit(loan) and loan.is_high_risk()

    def run_fraud_checks(self, loan: "LoanApplication") -> dict:
        """
        Run all fraud checks on the loan application.
        """
        flags = []

        if self.too_many_applications(loan.user):
            flags.append(FraudFlag.Reason.TOO_MANY_APPLICATIONS)

        if self.suspicious_email_domain(loan.user):
            flags.append(FraudFlag.Reason.SUSPICIOUS_ACTIVITY)

        if self._amount_exceeds_limit(loan):
            flags.append(FraudFlag.Reason.HIGH_RISK_PROFILE)

        if self.duplicate_account(loan.user):
            flags.append(FraudFlag.Reason.SUSPICIOUS_ACTIVITY)
            flags.append(FraudFlag.Reason.INCONSISTENT_INFORMATION)

        if flags:
            self.flag_loan(loan, flags)
            return {"status": FRAUD, "flags": flags}
        return {"status": CLEAN, "flags": []}  # at this point, no fraud detected


class AuditService:
    """
    NightWatch is a auditing service that monitors the status of the system and provides
    alerts in case of any issues.
    """

    @staticmethod
    def log_activity(action: str) -> None:
        """Log the action (approve, reject, flag) for auditing."""
        # TODO: create a log entry or maybe we should just use simple consle print
        logger.warning(f"[AUDIT] - {action} | Timestamp: {timezone.now()}")

    @staticmethod
    def _send_email_alert(message: str, recipients: list[str] = []) -> None:
        """
        Send an alert with the given message.
        """
        try:
            from django.conf import settings
            from django.core.mail import send_mail

            send_mail(
                subject="Fraud Alert",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
            )
        except Exception as e:
            logging.error(f"Failed to send email alert: {e}")

        logging.warning(f"Email Alert: {message} to {', '.join(recipients)}")

    @staticmethod
    def _send_sms_alert(message: str, recipients: list[str] = []) -> None:
        """
        Send an SMS alert with the given message.
        """
        logging.warning(f"SMS Alert: {message} to {', '.join(recipients)}")
        pass

    @staticmethod
    def alert(
        recipients: list[str],
        message: str = "Alert! Fraud detected!",
        channel: Literal["Email", "SMS"] = "Email",
    ) -> None:
        """
        Send an alert to the specified recipients.
        """
        from django.conf import settings

        admin_emails = settings.ADMIN_EMAILS

        if not recipients:
            # TODO: alert the admins
            recipients = admin_emails

        if channel == "SMS":
            AuditService._send_sms_alert(message, recipients)

        AuditService._send_email_alert(message, recipients)
        print(f"Alert sent to {', '.join(recipients)}: {message}")
