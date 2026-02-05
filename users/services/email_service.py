# users/services/email_service.py
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

class EmailService:
    @staticmethod
    def send_welcome_email(email, name, role):
        """Send welcome email to new user"""
        subject = f"Welcome to WorkConnect Uganda - {role.capitalize()} Account Created"
        html_message = render_to_string('emails/welcome.html', {
            'name': name,
            'role': role,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    
    @staticmethod
    def send_password_reset_email(email, name, reset_token):
        """Send password reset email"""
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{reset_token}"
        subject = "WorkConnect Uganda - Password Reset Request"
        html_message = render_to_string('emails/password_reset.html', {
            'name': name,
            'reset_url': reset_url,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    
    @staticmethod
    def send_password_reset_confirmation(email, name):
        """Send password reset confirmation email"""
        subject = "WorkConnect Uganda - Password Reset Successful"
        html_message = render_to_string('emails/password_reset_confirmation.html', {
            'name': name,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    
    @staticmethod
    def send_password_change_notification(email, name):
        """Send password change notification email"""
        subject = "WorkConnect Uganda - Password Changed"
        html_message = render_to_string('emails/password_change_notification.html', {
            'name': name,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    
    @staticmethod
    def send_verification_success_email(email, name):
        """Send verification success email"""
        subject = "WorkConnect Uganda - Account Verified Successfully"
        html_message = render_to_string('emails/verification_success.html', {
            'name': name,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )