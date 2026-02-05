# users/services/sms_service.py
import africastalking
from django.conf import settings

class SMSService:
    def __init__(self):
        if not settings.DEBUG and settings.AFRICASTALKING_API_KEY:
            africastalking.initialize(
                username=settings.AFRICASTALKING_USERNAME,
                api_key=settings.AFRICASTALKING_API_KEY
            )
            self.sms = africastalking.SMS
        else:
            self.sms = None
    
    def send_otp(self, phone, otp):
        """Send OTP via SMS"""
        message = f"Your WorkConnect verification code is: {otp}. Valid for 10 minutes."
        
        if self.sms and not settings.DEBUG:
            try:
                response = self.sms.send(message, [phone])
                return response
            except Exception as e:
                print(f"SMS sending failed: {e}")
                return None
        else:
            # In development, just log the message
            print(f"DEBUG SMS to {phone}: {message}")
            return {"status": "debug", "message": message}
    
    def send_payment_notification(self, phone, amount, reference):
        """Send payment notification"""
        message = f"Payment of UGX {amount:,} received. Reference: {reference}. Thank you for using WorkConnect."
        
        if self.sms and not settings.DEBUG:
            try:
                response = self.sms.send(message, [phone])
                return response
            except Exception as e:
                print(f"SMS sending failed: {e}")
                return None
        else:
            print(f"DEBUG SMS to {phone}: {message}")
            return {"status": "debug", "message": message}
    
    def send_salary_disbursement_notification(self, phone, amount, reference):
        """Send salary disbursement notification"""
        message = f"Your salary of UGX {amount:,} has been processed. Reference: {reference}. WorkConnect Uganda."
        
        if self.sms and not settings.DEBUG:
            try:
                response = self.sms.send(message, [phone])
                return response
            except Exception as e:
                print(f"SMS sending failed: {e}")
                return None
        else:
            print(f"DEBUG SMS to {phone}: {message}")
            return {"status": "debug", "message": message}
            