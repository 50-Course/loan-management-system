# Welcome! this library does so many things,
# Fundamentally, Its houses the test suite acrss the Loan and Fraud Detection Modules
# Tests is dividied at any point for user - customer, and in seperate test - for admin, for loan.


from datetime import timedelta
from unittest import TestCase
from unittest.mock import MagicMock

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase

from fraud.services import FraudDetectionService
from loans.models import LoanApplication
from users.models import Customer, LoanAdmin


class LoanApplicationTestCase(APITransactionTestCase):
    def setUp(self):
        self.customer = Customer.objects.create_user(
            username="customeruser",
            first_name="Bob",
            last_name="Smith",
            password="customerpassword",
            phone_number="1234567890",
            date_of_birth="1990-01-01",
            email="bsmith@example.com",
        )

    def test_single_entry_submission_successful(self):
        data = {
            "amount": 1000000,
            "purpose": "Personal",
            "customer": self.user.id,
        }
        response = self.client.post("/api/loans/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "PENDING")

    def test_cannot_submit_application_upon_rejected_application_same_day(self):
        #  user should not be able to submit a loan application if they
        #  were rejected on the same day
        rejected_loan = LoanApplication.objects.create(
            amount=2000,
            loan_type="Personal",
            customer=self.user,
            status="REJECTED",
            created_at=timezone.now(),
        )

        data = {
            "amount": 5000,
            "purpose": "Business",
            "customer": self.user.id,
        }

        response = self.client.post("/api/loans/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "You cannot submit a new application today due to a recent rejection.",
            response.data["error"],
        )

    def test_submission_requires_cooldown_period(self):
        LoanApplication.objects.create(
            amount=1000,
            loan_type="Personal",
            customer=self.user,
            status="PENDING",
            created_at=timezone.now() - timedelta(days=1),
        )

        data = {
            "amount": 1500,
            "loan_type": "Personal",
            "customer": self.user.id,
            "status": "PENDING",
        }

        response = self.client.post("/api/v1/loans/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "You must wait 24 hours before submitting another application.",
            response.data["error"],
        )

    def test_cannot_submit_application_with_invalid_data(self):
        data = {
            "amount": -1000,  # Invalid amount
            "purpose": "OTHER",
            "customer": self.user.id,
        }
        response = self.client.post("/api/loans/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", response.data["error"])
        self.assertIn("must be a positive number", response.data["error"]["amount"])


class LoanManagementTestCase(APITestCase):
    def setUp(self):
        self.admin = LoanAdmin.objects.create_user(
            username="adminuser",
            password="adminpassword",
            email="adminuser@example.com",
            phone_number="1234567890",
            role="ADMIN",
            first_name="Admin",
            last_name="User",
        )
        self.customer = Customer.objects.create_user(
            username="customeruser",
            first_name="Bob",
            last_name="Smith",
            password="customerpassword",
            phone_number="1234567890",
            date_of_birth="1990-01-01",
            email="bob.smith@example.com",
        )

        login_response = self.client.login(
            username="adminuser", password="adminpassword"
        )
        self.access_token = login_response.data.get("access")
        self.refresh_token = login_response.data.get("refresh")

        self.headers = {
            "HTTP_AUTHORIZATION": f"Bearer {self.access_token}",
            "HTTP_ACCEPT": "application/json",
            "HTTP_CONTENT_TYPE": "application/json",
        }
        self.client.credentials(**self.headers)

        # reauthorize the client with the admin user - and signed credentials
        self.client.force_authenticate(user=self.admin)

    def test_admin_can_view_all_applications(self):
        loan1 = LoanApplication.objects.create(
            amount=5000, loan_type="Personal", customer=self.customer, status="PENDING"
        )
        loan2 = LoanApplication.objects.create(
            amount=10000, loan_type="Business", customer=self.customer, status="PENDING"
        )

        response = self.client.get("/api/loans/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_admin_can_view_all_applications(self):
        # Admin should be able to view all loan applications
        LoanApplication.objects.create(
            amount_requested=5000, purpose="PERSONAL", user=self.customer
        )
        LoanApplication.objects.create(
            amount_requested=10000, purpose="BUSINESS", user=self.customer
        )
        response = self.client.get("/api/loans/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_admin_can_view_single_application(self):
        # Admin should be able to view a single loan application
        loan = LoanApplication.objects.create(
            amount_requested=5000, purpose="BUSINESS", user=self.customer
        )
        response = self.client.get(f"/api/loans/{loan.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], loan.id)

    def test_admin_can_approve_application(self):
        loan = LoanApplication.objects.create(
            amount_requested=7000, purpose="BUSINESS", user=self.customer
        )
        response = self.client.post(f"/api/loans/{loan.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanApplication.Status.APPROVED)

    def test_admin_can_reject_application(self):
        loan = LoanApplication.objects.create(
            amount_requested=8000, purpose="EDUCATION", user=self.customer
        )
        response = self.client.post(f"/api/loans/{loan.id}/reject/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanApplication.Status.REJECTED)

    def test_admin_can_flag_fraudlent_application(self):
        # from the dashboard, admin can flag a loan application as fraudulent
        from unittest.mock import patch

        loan = LoanApplication.objects.create(
            amount_requested=6_000_000,  # Exceeding maximum amount
            purpose="BUSINESS",
            user=self.customer,
        )

        with patch(
            "fraud.services.FraudDetectionService.is_fraudulent", return_value=True
        ):
            response = self.client.post(f"api/loans/{loan.id}/flag/", format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanApplication.Status.FLAGGED)


class FraudDetectionTestCase(TestCase):
    def setUp(self):
        self.beekeeper = FraudDetectionService()
        self.user1 = Customer.objects.create_user(
            first_name="John",
            last_name="Doe",
            username="user1",
            password="password123",
            phone_number="1234567890",
            date_of_birth="1995-01-01",
            email="user1@example.com",
        )
        self.user2 = Customer.objects.create_user(
            first_name="Jane",
            last_name="Doe",
            username="user2",
            password="password123",
            phone_number="0987654321",
            date_of_birth="1995-01-01",
            email="user1@example.com",  # Same email as user1, we would test this later
        )

    # Algorithm flags user for fraudlent attemts
    def test_flaggd_for_duplicate_accounts(self):
        # This test checks if a user is flagged for creating multiple accounts
        duplicate_user = Customer.objects.create_user(
            first_name="John",
            last_name="Doe",
            username="user3",
            password="password123",
            phone_number="1234567890",
            date_of_birth="1995-01-01",
            email="user3@example.com",
        )
        duplicate_user.email = "user1@example.com"  # Same email as existing user
        duplicate_user.save()
        # self.assertTrue(self.check_for_duplicate_accounts(duplicate_user)
        pass

    def test_flagged_for_same_user_credentials(self):
        # this test is a tricky one - but simply,
        # we flag the user, if an only if a duplicate
        # user, with same First Name and same Last Name, same D.O.B, registers with a different
        # email address.

        # test for fraudulent pattern when same user registers with different credentials
        Customer.objects.create_user(
            username="user2",
            password="password123",
            first_name="John",
            last_name="Doe",
            date_of_birth="1995-01-01",
            phone_number="0000000001",
            email="user2@otherdomain.com",
        )

        suspected_duplicates = Customer.objects.filter(
            first_name="John", last_name="Doe", date_of_birth="1995-01-01"
        )
        self.assertGreaterEqual(suspected_duplicates.count(), 2)

    def test_flagged_for_suspicious_email_domain(self):
        # user's email domain is used by more than 10 different users
        domain = "frauddomain.com"
        for i in range(12):
            Customer.objects.create_user(
                username=f"user{i}",
                password="password",
                phone_number=f"0700000000{i}",
                email=f"user{i}@{domain}",
                date_of_birth="1990-01-01",
            )
        user = Customer.objects.get(username="user0")
        self.assertTrue(self.beekeeper.suspicious_email_domain(user))

    def test_flagged_user_ineligible_for_application(self):
        # a flagged user is not eligible to apply for a loan
        flagged_user = Customer.objects.create_user(
            first_name="Flagged",
            last_name="User",
            username="flaggeduser",
            password="password123",
            phone_number="1234567890",
            date_of_birth="1995-01-01",
            email="flaggeduser@example.com",
        )
        flagged_user.flagged_for_fraud = True
        flagged_user.save()

        # Attempt to apply for a loan
        data = {
            "amount": 1000000,
            "purpose": "PERSONAL",
            "customer": flagged_user.id,
        }

        self.assertTrue(flagged_user.flagged_for_fraud)
        self.client.login(username="flaggeduser", password="password123")

        response = self.client.post("/api/loan/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Algorithm flags loans for fraudulent patterns
    def test_flagged_for_multiple_entries_within_24h(self):
        for _ in range(4):
            LoanApplication.objects.create(
                amount_requested=1000,
                purpose="BUSINESS",
                user=self.user1,
                date_applied=timezone.now(),
            )
        self.assertTrue(self.beekeeper.too_many_applications(self.user1))

    def test_flagged_for_exceeding_maximum_amount(self):
        # maximum amount is set to 5,000,000 if a user applies for more than 5,000,000, they are flagged
        loan = LoanApplication.objects.create(
            amount_requested=6_000_000,
            purpose="BUSINESS",
            user=self.user1,
        )
        result = self.beekeeper.run_fraud_checks(loan)
        self.assertTrue(result["status"] == "fraudulent")
        self.assertIn(
            "Loan amount exceeds the maximum limit",
            result["flags"],
        )

    def test_flagged_for_exagreated_needs(self):
        # TODO: we would use a simple calculator to determine, earning power
        # and therefore base a 5-8% range (random) (increase or decrease) of the
        # requested amount
        pass
