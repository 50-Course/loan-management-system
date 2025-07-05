# Welcome! this library does so many things,
# Fundamentally, Its houses the test suite acrss the Loan and Fraud Detection Modules
# Tests is dividied at any point for user - customer, and in seperate test - for admin, for loan.


from unittest import TestCase
from unittest.mock import MagicMock

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase

from loans.models import LoanApplication
from users.models import Customer, LoanAdmin


class LoanApplicationTestCase(APITransactionTestCase):
    def setUp(self):
        self.user = Customer.objects.create_user(
            username="customer1",
            password="customerpassword",
            phone_number="12345678901",
            date_of_birth="1995-01-01",
        )
        self.client.login(username="customer1", password="customerpassword")

    def test_single_entry_submission_successful(self):
        data = {
            "amount": 1000000,
            "purpose": "Personal",
            "customer": self.user.id,
        }
        response = self.client.post("/api/loans/", data, format="json")

        self.assertEqual(response.status_code, status=status.HTTP_201_CREATED)
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
        self.assertEqual(response.status_code, status=status.HTTP_400_BAD_REQUEST)
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

        self.assertEqual(response.status_code, status=status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", response.data["error"])
        self.assertIn("must be a positive number", response.data["error"]["amount"])


class LoanManagementTestCase(APITestCase):
    def setUp(self):
        self.admin = LoanAdmin.objects.create_user(
            username="adminuser", password="adminpassword", role="ADMIN"
        )
        self.customer = Customer.objects.create_user(
            username="customeruser",
            password="customerpassword",
            phone_number="1234567890",
            date_of_birth="1990-01-01",
        )
        self.client.login(username="adminuser", password="adminpassword")

    def test_admin_can_view_all_applications(self):
        loan1 = LoanApplication.objects.create(
            amount=5000, loan_type="Personal", customer=self.customer, status="PENDING"
        )
        loan2 = LoanApplication.objects.create(
            amount=10000, loan_type="Business", customer=self.customer, status="PENDING"
        )

        response = self.client.get("/api/loans/")
        self.assertEqual(response.status_code, status=status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_admin_can_view_single_application(self):
        loan = LoanApplication.objects.create(
            amount=5000, loan_type="Personal", customer=self.customer, status="PENDING"
        )
        response = self.client.get(f"/api/loans/{loan.id}/")
        self.assertEqual(response.status_code, status=status.HTTP_200_OK)
        self.assertEqual(response.data["id"], loan.id)
        self.assertIn("amount_requested", response.data)
        self.assertIn("status", response.data)

    def test_admin_can_approve_application(self):
        loan = LoanApplication.objects.create(
            amount=5000, loan_type="Personal", customer=self.customer, status="PENDING"
        )
        response = self.client.post(f"/api/loans/{loan.id}/approve/")
        self.assertEqual(response.status_code, status=status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertEqual(loan.status, "APPROVED")

    def test_admin_can_reject_application(self):
        loan = LoanApplication.objects.create(
            amount=5000, loan_type="Personal", customer=self.customer, status="PENDING"
        )
        response = self.client.post(f"/api/loans/{loan.id}/reject/")
        self.assertEqual(response.status_code, status=status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertEqual(loan.status, "REJECTED")

    def test_admin_can_update_application_status(self):
        # Admin should be able to update the status of an application
        pass


class FraudDetectionTestCase(TestCase):
      def setUp(self):
        self.user1 = Customer.objects.create_user(
            username="user1",
            password="password123",
            phone_number="1234567890",
            date_of_birth="1995-01-01",
            email="user1@example.com"
        )
        self.user2 = Customer.objects.create_user(
            username="user2",
            password="password123",
            phone_number="0987654321",
            date_of_birth="1995-01-01",
            email="user1@example.com"   # Same email as user1, we would test this later
        )
        
    # Algorithm flags user for fraudlent attemts
    def test_flaggd_for_duplicate_accounts():
        # This test checks if a user is flagged for creating multiple accounts
        duplicate_user = Customer.objects.create_user(
            username="user3",
            password="password123",
            phone_number="1234567890",
            date_of_birth="1995-01-01",
            email="user3@example.com"
        )
        duplicate_user.email = "user1@example.com"  # Same email as existing user
        duplicate_user.save()
        # self.assertTrue(self.check_for_duplicate_accounts(duplicate_user)
        pass

    def test_flagged_for_same_user_credentials():
        # this test is a tricky one - but simply,
        # we flag the user, if an only if a duplicate
        # user, with same First Name and same Last Name, same D.O.B, registers with a different
        # email address.

        # test for fraudulent pattern when same user registers with different credentials
        duplicate_user = Customer.objects.create_user(
            username="user4",
            password="password123",
            phone_number="0987654321",
            date_of_birth="1995-01-01",
            email="user4@example.com"
        )
        duplicate_user.first_name = "John"
        duplicate_user.last_name = "Doe"
        duplicate_user.save()
        self.assertTrue(self.check_for_duplicate_credentials(duplicate_user))

    def test_flagged_for_same_email():
        # user's email domain is used by more than 10 different users
        pass

    def test_flagged_user_ineligible_for_application():
        pass

    # Algorithm flags loans for fraudulent patterns
    def test_flagged_for_multiple_entries_within_24h():
        pass

    def test_flagged_for_exceeding_maximum_amount():
        # maximum amount is set to 5,000,000
        # if a user applies for more than 5,000,000, they are flagged

        data = {
            "amount": 6000000,  # Exceeding maximum amount
            "purpose": "Business",
            "customer": self.user1.id,
        }
        response = self.client.post("/api/loans/", data, format="json")
        self.assertIn('status', response.data)
        self.assertEqual(response.status_code, status=status.HTTP_400_BAD_REQUEST)

        # i guess we should mock our fraud detection service here

    def test_flagged_for_exagreated_needs():
        # we would use a simple calculator to determine, earning power
        # and therefore base a 5-8% range (random) (increase or decrease) of the
        # requested amount
        pass
