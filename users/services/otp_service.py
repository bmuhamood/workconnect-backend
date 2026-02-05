import pyotp
import random
import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

class OTPService:
    """Service for OTP generation and validation"""
    
    @staticmethod
    def generate_otp(phone):
        """
        Generate 6-digit OTP valid for 10 minutes
        
        Development: Prints to console and optionally sends SMS to sandbox numbers
        Production: Sends SMS via Africa's Talking
        """
        # Clean phone number format
        phone = OTPService._format_phone_number(phone)
        
        # Generate OTP
        otp = str(random.randint(100000, 999999))
        
        # Store in cache
        cache.set(f'otp_{phone}', otp, timeout=600)
        cache.set(f'otp_attempts_{phone}', 0, timeout=600)
        
        # Always log for debugging
        logger.info(f"OTP generated for {phone}: {otp}")
        
        # Determine how to send OTP
        if OTPService._should_send_sms(phone):
            sms_sent = OTPService._send_sms(phone, otp)
            
            if sms_sent:
                print(f"\n✅ OTP sent via SMS to {phone}")
            else:
                print(f"\n⚠️ SMS failed. Displaying OTP for {phone}: {otp}")
        else:
            # Development: Show OTP in console
            OTPService._display_otp_in_console(phone, otp)
        
        return otp
    
    @staticmethod
    def _format_phone_number(phone):
        """Format phone number for Africa's Talking"""
        # Remove any spaces, dashes, etc.
        phone = ''.join(filter(str.isdigit, str(phone)))
        
        # Convert to international format for Uganda
        if phone.startswith('0'):
            phone = '+256' + phone[1:]  # Ugandan numbers starting with 0
        elif phone.startswith('256') and len(phone) == 12:
            phone = '+' + phone
        elif phone.startswith('7') and len(phone) == 9:
            phone = '+256' + phone
        
        return phone
    
    @staticmethod
    def _should_send_sms(phone):
        """
        Determine if we should send SMS:
        - In production: Always send
        - In development: Only send to sandbox-allowed numbers
        - Or if SMS_ENABLED is True in settings
        """
        # Check if SMS is globally enabled
        if getattr(settings, 'SMS_ENABLED', False):
            return True
        
        # In development, check if it's a sandbox-allowed number
        if settings.DEBUG:
            # Africa's Talking sandbox only allows specific test numbers
            # Add your test numbers here
            sandbox_numbers = [
                '+254711XXXYYY',  # Replace with your sandbox numbers
                '+2567XXXXXXXX',  # Your test Ugandan numbers
            ]
            
            # Check if this phone is in sandbox allowed list
            for test_number in sandbox_numbers:
                if test_number.replace('X', '').replace('Y', '') in phone:
                    return True
        
        return False
    
    @staticmethod
    def _display_otp_in_console(phone, otp):
        """Display OTP in console for development"""
        print(f"\n{'='*60}")
        print(f"📱 OTP VERIFICATION (DEVELOPMENT MODE)")
        print(f"{'='*60}")
        print(f"Phone: {phone}")
        print(f"OTP Code: {otp}")
        print(f"Valid for: 10 minutes")
        print(f"{'='*60}")
        
        # Also save to a temporary file for easy access
        try:
            with open('/tmp/workconnect_otp.txt', 'w') as f:
                f.write(f"Phone: {phone}\nOTP: {otp}\n")
        except:
            pass
    
    @staticmethod
    def _send_sms(phone, otp):
        """
        Send OTP via Africa's Talking
        Returns: True if sent successfully, False otherwise
        """
        try:
            import africastalking
            
            # Initialize Africa's Talking
            africastalking.initialize(
                username=settings.AFRICASTALKING_USERNAME,
                api_key=settings.AFRICASTALKING_API_KEY
            )
            
            sms = africastalking.SMS
            
            # Craft message
            message = f"Your WorkConnect verification code is: {otp}. Valid for 10 minutes."
            
            # In sandbox mode, we might need to use a specific sender ID or no sender ID
            sender_id = None
            if hasattr(settings, 'AFRICASTALKING_SENDER_ID') and settings.AFRICASTALKING_SENDER_ID:
                sender_id = settings.AFRICASTALKING_SENDER_ID
            
            # Send SMS
            if sender_id:
                response = sms.send(message, [phone], sender_id=sender_id)
            else:
                response = sms.send(message, [phone])
            
            # Check response
            if response and response.get('SMSMessageData', {}).get('Recipients'):
                recipient = response['SMSMessageData']['Recipients'][0]
                
                if recipient.get('status') == 'Success':
                    logger.info(f"SMS sent to {phone}: {recipient.get('messageId')}")
                    print(f"📱 SMS sent to {phone} (Message ID: {recipient.get('messageId')})")
                    return True
                else:
                    logger.warning(f"SMS failed for {phone}: {recipient.get('status')}")
                    return False
            
            return False
            
        except ImportError:
            logger.error("Africa's Talking SDK not installed. Run: pip install africastalking")
            print("❌ Africa's Talking SDK not installed. Install with: pip install africastalking")
            return False
        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            print(f"❌ SMS sending failed: {str(e)}")
            return False
    
    @staticmethod
    def verify_otp(phone, user_otp):
        """
        Verify OTP with attempt limiting
        Returns: (is_valid, message)
        """
        # Format phone number
        phone = OTPService._format_phone_number(phone)
        
        attempts_key = f'otp_attempts_{phone}'
        attempts = cache.get(attempts_key, 0)
        
        # Limit to 5 attempts
        if attempts >= 5:
            logger.warning(f"Too many OTP attempts for {phone}")
            return False, "Too many attempts. Please request a new OTP."
        
        stored_otp = cache.get(f'otp_{phone}')
        
        if not stored_otp:
            logger.warning(f"OTP expired or not found for {phone}")
            return False, "OTP expired or not found. Please request a new OTP."
        
        # Increment attempts
        cache.incr(attempts_key)
        
        if stored_otp == user_otp:
            # Clear OTP and attempts on successful verification
            cache.delete(f'otp_{phone}')
            cache.delete(attempts_key)
            logger.info(f"OTP verified successfully for {phone}")
            return True, "OTP verified successfully."
        
        remaining_attempts = 5 - (attempts + 1)
        logger.warning(f"Invalid OTP attempt for {phone}. {remaining_attempts} attempts left")
        
        if remaining_attempts > 0:
            return False, f"Invalid OTP. {remaining_attempts} attempts remaining."
        return False, "Invalid OTP."
    
    @staticmethod
    def resend_otp(phone):
        """Resend OTP to phone"""
        return OTPService.generate_otp(phone)
    
    @staticmethod
    def check_otp_status(phone):
        """Check if OTP exists and get remaining time"""
        phone = OTPService._format_phone_number(phone)
        
        otp = cache.get(f'otp_{phone}')
        if not otp:
            return None, 0
        
        # Get remaining time (in seconds)
        ttl = cache.ttl(f'otp_{phone}')
        
        return otp, ttl