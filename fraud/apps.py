from django.apps import AppConfig

app_label = "fraud_management"


class FraudConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fraud"
    verbose_name = "Fraud Management"
