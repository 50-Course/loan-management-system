from django.contrib.auth.models import AbstractUser
from django.db import models

# Actors: Admin, Customer
#
# Plan

class BaseUser(AbstractUser):
    class RoleType(models.TextChoices):
        ADMIN = "admin"
        CUSTOMER = "customer"

    role = models.CharField(choices=RoleType.choices, default=RoleType.CUSTOMER)
