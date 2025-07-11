# Generated by Django 5.2.4 on 2025-07-05 12:25

import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('role', models.CharField(choices=[('ADMIN', 'Admin'), ('CUSTOMER', 'Customer')], default='CUSTOMER')),
                ('first_name', models.CharField(help_text='The first name of the user. Required for all users.', max_length=30, verbose_name='First Name')),
                ('last_name', models.CharField(help_text='The last name of the user. Required for all users.', max_length=30, verbose_name='Last Name')),
                ('email', models.EmailField(help_text='The email address of the user. Required for all users.', max_length=254, verbose_name='Email Address')),
                ('phone_number', models.CharField(blank=True, help_text="User's phone number - must be 11 digits, without the country code. Required for customers.", max_length=11, null=True, unique=True)),
                ('date_of_birth', models.DateField(blank=True, help_text='The date of birth of the user. Required for customers.', null=True, verbose_name='Date of Birth')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. Overides default', related_name='baseuser_set', related_query_name='baseuser', to='auth.group')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text="Specific permissions for this user. Overrides django's default permissions.", related_name='baseuser_set', related_query_name='baseuser', to='auth.permission')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('baseuser_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Customer',
                'verbose_name_plural': 'Customers',
            },
            bases=('users.baseuser',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='LoanAdmin',
            fields=[
                ('baseuser_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Loan Admin',
                'verbose_name_plural': 'Loan Admins',
            },
            bases=('users.baseuser',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
