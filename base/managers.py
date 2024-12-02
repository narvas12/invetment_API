from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from core import settings
from django.contrib.auth.models import BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a `User` with an email, phone, and password."""
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password) 
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a `User` with superuser (admin) permissions."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class EmailNotificationManager:

    @staticmethod
    def send_transaction_status_email(user, transaction_type, amount, status):
        subject = f"Your {transaction_type.capitalize()} Transaction has been {status.capitalize()}"
        context = {
            'user': user,
            'transaction_type': transaction_type,
            'amount': amount,
            'status': status,
        }

        html_message = render_to_string('email/deposit_status_change.html', context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

    @staticmethod
    def send_welcome_email(user):
        subject = "Welcome to our platform!"
        context = {'user': user}

        html_message = render_to_string('email/welcome_email.html', context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

    @staticmethod
    def send_transaction_initiation_email(user, transaction_type, amount, transaction=None, withdrawal_account=None):
        subject_user = f"{transaction_type.capitalize()} Transaction Initiated"
        context_user = {
            'user': user,
            'transaction_type': transaction_type,
            'amount': amount,
            'transaction': transaction,
            'withdrawal_account': withdrawal_account,
        }

        html_message_user = render_to_string('email/user_transaction_notification.html', context_user)
        plain_message_user = strip_tags(html_message_user)

        send_mail(
            subject=subject_user,
            message=plain_message_user,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message_user,
            fail_silently=False,
        )

        company_email = settings.COMPANY_EMAIL
        subject_company = f"New {transaction_type.capitalize()} Initiated by {user.get_full_name()}"
        context_company = {
            'user': user,
            'transaction_type': transaction_type,
            'amount': amount,
        }

        html_message_company = render_to_string('email/company_transaction_notification.html', context_company)
        plain_message_company = strip_tags(html_message_company)

        send_mail(
            subject=subject_company,
            message=plain_message_company,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[company_email],
            html_message=html_message_company,
            fail_silently=False,
        )

    @staticmethod
    def send_deposit_confirmation_to_company(user, wallet_credited, transaction_hash):
        subject = "New Deposit Confirmation"
        company_email = settings.COMPANY_EMAIL  

        context = {
            'user': user,
            'wallet_credited': wallet_credited,
            'transaction_hash': transaction_hash,
        }

        html_message = render_to_string('email/deposit_comfirmation.html', context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[company_email],
            html_message=html_message,
            fail_silently=False,
        )

    @staticmethod
    def send_bonus_email(recipient_email, recipient_full_name, amount):
        subject = 'Congratulations! Bonus Awarded to You!'
        context = {
            'recipient_full_name': recipient_full_name,
            'amount': amount,
        }

        html_message = render_to_string('email/bonus_awarded_email.html', context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )