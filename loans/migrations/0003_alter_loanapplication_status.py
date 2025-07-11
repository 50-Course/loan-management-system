# Generated by Django 5.2.4 on 2025-07-05 12:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loans', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='loanapplication',
            name='status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('FLAGGED', 'Flagged for Fraud')], default='PENDING', help_text='Current status of the loan application', max_length=20),
        ),
    ]
