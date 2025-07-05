from django.contrib.auth.models import AbstractUser
from django.db import models


class BaseUser(AbstractUser):
    class RoleType(models.TextChoices):
        ADMIN = "ADMIN"
        CUSTOMER = "CUSTOMER"

    role = models.CharField(choices=RoleType.choices, default=RoleType.CUSTOMER)
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="baseuser_set",
        blank=True,
        help_text="The groups this user belongs to. Overides default",
        related_query_name="baseuser",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="baseuser_set",
        blank=True,
        help_text="Specific permissions for this user. Overrides django's default permissions.",
        related_query_name="baseuser",
    )
    first_name = models.CharField(
        max_length=30,
        verbose_name="First Name",
        help_text="The first name of the user. Required for all users.",
    )
    last_name = models.CharField(
        max_length=30,
        verbose_name="Last Name",
        help_text="The last name of the user. Required for all users.",
    )
    phone_number = models.CharField(
        max_length=11,
        unique=True,
        blank=True,
        null=True,
        help_text="User's phone number - must be 11 digits, without the country code. Required for customers.",
    )
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date of Birth",
        help_text="The date of birth of the user. Required for customers.",
    )

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"


class LoanAdmin(BaseUser):
    """
    Represents an admin user who manages loan applications.
    """

    REQUIRED_FIELDS = ["role", "first_name", "last_name", "username"]

    class Meta:
        verbose_name = "Loan Admin"
        verbose_name_plural = "Loan Admins"

    def __str__(self):
        last_name_inital = str(self.last_name)[0]
        return f"{self.get_short_name()} {last_name_inital}." or f"{self.username}"


class Customer(BaseUser):
    """
    Represents a customer who applies for loans.

    As a measure to prevent fraud, we require customers to provide their phone number and date of birth.
    """

    # phone_number = models.CharField(
    #     max_length=11,
    #     unique=True,
    #     help_text="Customer's phone number - must be 11 digits, without the country code",
    # )
    # date_of_birth = models.DateField(
    #     help_text="Customer's date of birth",
    # )

    # we require the phone number, for authentication
    # - the phone number without the leading zero
    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["role", "first_name", "last_name"]

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        last_name_inital = str(self.last_name)[0]
        return f"{self.get_short_name()} {last_name_inital}."
