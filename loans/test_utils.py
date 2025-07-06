# A combination of helper functions/factories for  testing purposes.

import random

from django.urls import reverse
from rest_framework.test import APIClient

from loans.models import LoanApplication
from users.models import Customer, LoanAdmin


def unique_phone() -> str:
    # generate a random four digit prefix for phone numbers
    # and append a random 7 digit number to it
    prefix = random.choice(["070", "080", "090", "081", "091"])
    return f"{prefix}{random.randint(10000000, 99999999)}"


_last_email_domain = None  # persist domain across calls for same_domain=True


def unique_email(
    username=None,
    domain=None,
    same_domain=False,
) -> str:
    global _last_email_domain

    avail_domains = [
        "example.com",
        "test.com",
        "demo.com",
        "sample.com",
        "fake.com",
        "frauddomain.com",
    ]

    if domain:
        chosen_domain = domain

    elif same_domain:
        if not _last_email_domain:
            _last_email_domain = random.choice(avail_domains)
        chosen_domain = _last_email_domain
    else:
        chosen_domain = random.choice(avail_domains)

    if username:
        return f"{username}@{chosen_domain}"
    return f"user{random.randint(1000, 9999)}@{chosen_domain}"


def unique_username(first_name=None, last_name=None, username=None, email=None) -> str:
    # i wish i had factory boy here, so i go lean development and not
    # worry about unique constraints errors or factory methods mocking :eyes:

    # a combo of first name, last name and email, special characters all unique 8 - and randomized
    if first_name and last_name:
        return f"{first_name.lower()}.{last_name.lower()}.{random.randint(1000, 9999)}"
    elif email:
        return email.split("@")[0] + f".{random.randint(1000, 9999)}"
    else:
        return f"user.{random.randint(1000, 9999)}"


def fake_dob() -> str:
    # assuming, customers are born between 1970 and 2000
    year = random.randint(1970, 2000)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"


def unique_pass() -> str:
    # generate a random password with 8 characters, including letters and digits
    characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    special_characters = "!@#$%^&*()-_=+[]{}|;:,.<>?/"
    return "".join(random.choice(characters + special_characters) for _ in range(8))


def fake_customer(password=None, **kwargs) -> tuple["Customer", str]:
    """
    first_name and last_name must be provided in kwargs, returns a full customer object and the password used for login
    """
    if "first_name" not in kwargs or "last_name" not in kwargs:
        raise ValueError("first_name and last_name must be provided in kwargs")

    email_domain = kwargs.pop("email_domain", None)
    email = kwargs.pop("email", None)
    if not email:
        # if email is not provided, generate a unique email
        # if email_domain is provided, use that domain, otherwise use a random domain
        email = (
            unique_email()
            if not email_domain
            else unique_email(same_domain=True, domain=email_domain)
        )

    dob = kwargs.pop("date_of_birth", None)
    password = password or unique_pass()

    customer = Customer.objects.create_user(
        username=unique_username(email),
        email=email,
        phone_number=unique_phone(),
        date_of_birth=fake_dob() if not dob else dob,
        password=password,
        role="CUSTOMER",
        **kwargs,
    )
    return customer, password


def fake_admin(password=None) -> tuple["LoanAdmin", str]:
    password = password or unique_pass()
    admin = LoanAdmin.objects.create_user(
        username=unique_username("admin"),
        password=password,
        email=unique_email("admin"),
        role="ADMIN",
        first_name="Admin",
        last_name="User",
    )
    return admin, password


def fake_loan(customer: "Customer", **kwargs) -> "LoanApplication":
    status = kwargs.get("status", None)
    purpose = kwargs.pop("purpose", None)
    amount_requested = kwargs.pop("amount_requested", None)
    return LoanApplication.objects.create(
        user=customer,
        amount_requested=amount_requested or random.randint(1000, 4_999_999),
        purpose=purpose or random.choice(LoanApplication.Purpose.choices),
        status="PENDING" if not status else status,
    )


def authenticate_user(user, password=None) -> "APIClient":
    # custom function to authenticate a user, adds the JWT token and reauthenticate user for full access
    client = APIClient()
    login_url = reverse("login")
    password = password or "defaultpass123"

    response = client.post(
        login_url,
        {"username": user.username, "password": password},
        format="json",
    )
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.data}")

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['data']['access']}")
    return client
