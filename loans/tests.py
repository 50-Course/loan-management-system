# Welcome! this library does so many things,
# Fundamentally, Its houses the test suite acrss the Loan and Fraud Detection Modules
# Tests is dividied at any point for user - customer, and in seperate test - for admin, for loan.

import random
import unittest
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase, APITransactionTestCase

from fraud.constants import FRAUD
from fraud.models import FraudFlag
from fraud.services import FraudDetectionService
from loans.models import LoanApplication
from loans.test_utils import authenticate_user
from users.models import Customer

from .test_utils import (_last_email_domain, fake_admin, fake_customer,
                         fake_loan)


class LoanApplicationTestCase(APITransactionTestCase):
    def setUp(self):
        self.customer, self.password = fake_customer(first_name="John", last_name="Doe")
        self.client = authenticate_user(self.customer, password=self.password)

        self.submit_url = reverse("submit_loan")
        self.find_loan_url = lambda id: reverse("retrieve_loan", kwargs={"id": id})
        self.my_loans_url = reverse("my_loans")

    def test_single_entry_submission_successful(self):
        data = {"amount_requested": 1_000_000, "purpose": "PERSONAL"}
        response = self.client.post(self.submit_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("status", response.data["data"])
        self.assertEqual(response.data["data"]["status"], "PENDING")

    def test_cannot_submit_application_upon_rejected_application_same_day(self):
        #  customer should not be able to submit a loan application if they were rejected on the same day
        rejected_loan = fake_loan(self.customer, status="REJECTED")

        data = {"amount_requested": 5000, "purpose": "EDUCATION"}
        response = self.client.post(self.submit_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["status"], "error")

    def test_submission_requires_cooldown_period(self):
        # user must wait 24 hours before submitting another application
        now = timezone.now()
        fake_loan(self.customer, date_applied=now - timedelta(hours=23))  # an hour left

        data = {"amount_requested": 1500, "purpose": "PERSONAL"}
        response = self.client.post(self.submit_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_submit_application_with_invalid_data(self):
        data = {"amount_requested": -1000, "purpose": "OTHER"}
        response = self.client.post(self.submit_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_can_view_own_loans(self):
        # Customer should be able to view their own loan applications
        fake_loan(self.customer, status="APPROVED")
        response = self.client.get(self.my_loans_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_can_view_single_loan(self):
        # Customer should be able to view a single loan application
        loan = fake_loan(self.customer, amount_requested=100_000, purpose="EDUCATION")
        response = self.client.get(self.find_loan_url(loan.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], self.customer.get_full_name())
        self.assertTrue(
            Decimal.compare(Decimal(response.data["amount"]), Decimal(100_000.00)) == 0
        )
        self.assertEqual(response.data["purpose"], "EDUCATION")


class LoanManagementTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.all_loans_url = reverse("all_loans")
        self.customer_loan_url = lambda id: reverse(
            "retrieve_customer_loan", kwargs={"id": id}
        )
        self.approve_url = lambda id: reverse("approve_loan", kwargs={"id": id})
        self.reject_url = lambda id: reverse("reject_loan", kwargs={"id": id})
        self.flag_url = lambda id: reverse("flag_loan", kwargs={"id": id})
        self.flagged_loans_url = lambda id: reverse("flagged_loans", kwargs={"id": id})

        self.admin, adminpass = fake_admin()
        self.customer, _ = fake_customer(first_name="Jane", last_name="Doe")
        self.client = authenticate_user(self.admin, password=adminpass)

    def test_admin_can_view_all_applications(self):
        # Admin should be able to view all loan applications
        fake_loan(self.customer, status="APPROVED")
        fake_loan(self.customer, status="REJECTED")
        fake_loan(self.customer, status="APPROVED")

        response = self.client.get(self.all_loans_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 3)

    def test_admin_can_view_single_application(self):
        # Admin should be able to view a single loan application
        loan = fake_loan(self.customer, amount_requested=5000, purpose="BUSINESS")

        response = self.client.get(self.customer_loan_url(loan.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("loan_id", response.data)
        self.assertIn("purpose", response.data)
        self.assertTrue(
            response.data["user_profile"]["full_name"] == self.customer.get_full_name()
        )
        self.assertTrue(
            Decimal.compare(
                Decimal(response.data["amount_requested"]), Decimal(5000.00)
            )
            == 0
        )

    def test_admin_can_approve_application(self):
        loan = fake_loan(self.customer, purpose="MEDICAL")
        response = self.client.post(self.approve_url(loan.id), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        loan.refresh_from_db()
        self.assertTrue(loan.status == LoanApplication.Status.APPROVED)
        self.assertTrue(
            loan.fraud_flags.exists() is False
        )  # No fraud flags after approval

    def test_admin_can_reject_application(self):
        # we can reject an application even if its not flagged for suspicious activity
        loan = fake_loan(self.customer)
        response = self.client.post(self.reject_url(loan.id), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanApplication.Status.REJECTED)

    def test_admin_can_flag_fraudlent_application(self):
        # from the dashboard, admin can flag a loan application as fraudulent
        from unittest.mock import patch

        # exceeded maximum amount
        loan = fake_loan(self.customer, amount_requested=6_000_000, purpose="BUSINESS")
        payload = [
            {
                "reason": "HIGH_RISK_PROFILE",
                "comments": "User has high-risk indicators",
            },
            {
                "reason": "TOO_MANY_APPLICATIONS",
                "comments": "Applied multiple times recently",
            },
        ]

        # mock to identify if requested amount pattern is suspicious
        response = self.client.post(self.flag_url(loan.id), data=payload, format="json")
        loan.refresh_from_db()
        self.assertEqual(loan.status, "FLAGGED")
        self.assertTrue(loan.fraud_flags.exists())
        self.assertTrue(loan.fraud_flags.count() > 0)
        self.assertSetEqual(
            set(loan.fraud_flags.values_list("reason", flat=True)),
            {"HIGH_RISK_PROFILE", "TOO_MANY_APPLICATIONS"},
        )


class FraudDetectionTestCase(TestCase):
    def setUp(self):
        self.beekeeper = FraudDetectionService()
        self.user1, _ = fake_customer(first_name="Bob", last_name="Smith")
        self.user2, _ = fake_customer(
            first_name="Alice", last_name="Johnson"
        )  # TODO: use, same email as user1, we would test this later
        self.submit_url = reverse("submit_loan")
        _last_email_domain = None  # avoid flaky tests due to email domain changes

    # Algorithm flags user for fraudlent attemts
    def test_flaggd_for_duplicate_accounts(self):
        # This test checks if a user is flagged for creating multiple accounts
        duplicate_user, _ = fake_customer(
            email=self.user1.email,
            first_name="John",
            last_name="Doe",
        )
        self.assertTrue(self.beekeeper.duplicate_account(duplicate_user))

    def test_flagged_for_same_user_credentials(self):
        # this test is a tricky one - but simply, we flag the user, if an only if a duplicate
        # user, with same First Name and same Last Name, same D.O.B, registers with a different email address.

        # test for fraudulent pattern when same user registers with different credentials
        fake_customer(
            email="user2@otherdomain.com",
            first_name="John",
            last_name="Doe",
            date_of_birth="1995-01-01",
        )
        suspected_duplicates = Customer.objects.filter(
            first_name="John", last_name="Doe", date_of_birth="1995-01-01"
        )
        self.assertGreaterEqual(suspected_duplicates.count(), 1)

    def test_flagged_for_suspicious_email_domain(self):
        # user's email domain is used by more than 10 different users
        domain = "frauddomain.com"
        for i in range(12):
            fake_customer(
                first_name=f"user{i}", last_name=f"user{i}", email_domain=domain
            )
        matches = Customer.objects.filter(email__contains=domain)
        self.assertGreaterEqual(matches.count(), 10)

        user = matches.first()
        self.assertTrue(self.beekeeper.suspicious_email_domain(user))

    def test_flagged_user_ineligible_for_application(self):
        # a flagged user is not eligible to apply for a loan
        flagged_user, userpass = fake_customer(first_name="Flagged", last_name="User")
        flagged_user.flagged_for_fraud = True
        flagged_user.save()

        # Attempt to apply for a loan
        data = {"amount_requested": 1000000, "purpose": "PERSONAL"}

        client = authenticate_user(flagged_user, password=userpass)
        response = client.post(self.submit_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Algorithm flags loans for fraudulent patterns
    def test_flagged_for_multiple_entries_within_24h(self):
        for i in range(4):
            fake_loan(self.user1, date_applied=(timezone.now() + timedelta(hours=i)))
        self.assertTrue(self.beekeeper.too_many_applications(self.user1))

    def test_flagged_for_exceeding_maximum_amount(self):
        # maximum amount is set to 5,000,000 if a user applies for more than 5,000,000, they are flagged
        loan = fake_loan(self.user1, amount_requested=6_000_000)
        result = self.beekeeper.run_fraud_checks(loan)

        loan.refresh_from_db()

        self.assertTrue(result["status"])
        self.assertTrue(loan.status == "FLAGGED")
        self.assertIn(
            FraudFlag.Reason.HIGH_RISK_PROFILE,
            result["flags"],
        )

    @unittest.skip("Would implement later")
    def test_flagged_for_exagreated_needs(self):
        # TODO: we would use a simple calculator to determine, earning power
        # and therefore base a 5-8% range (random) (increase or decrease) of the
        # requested amount
        pass
