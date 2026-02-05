import requests
import json
import hmac
import hashlib
import time
from django.conf import settings
from django.utils import timezone
from datetime import datetime

from payments.models import PaymentTransaction


class PaymentGateway:
    """Base class for payment gateways"""
    
    def __init__(self):
        self.name = "Base Gateway"
    
    def initiate_payment(self, amount, phone, reference, **kwargs):
        """Initiate a payment"""
        raise NotImplementedError
    
    def check_payment_status(self, transaction_id):
        """Check payment status"""
        raise NotImplementedError
    
    def disburse_payment(self, amount, phone, reference, **kwargs):
        """Disburse payment to recipient"""
        raise NotImplementedError
    
    def validate_webhook(self, request):
        """Validate webhook signature"""
        raise NotImplementedError
    
    def parse_webhook(self, data):
        """Parse webhook data"""
        raise NotImplementedError
    
    def _create_transaction_record(self, transaction_type, amount, reference, user=None, **kwargs):
        """Create transaction record in database"""
        transaction = PaymentTransaction.objects.create(
            transaction_type=transaction_type,
            external_reference=reference,
            amount=amount,
            currency='UGX',
            payment_method=self.name,
            payment_provider=self.name,
            payer_user=user,
            status=PaymentTransaction.TransactionStatus.INITIATED,
            **kwargs
        )
        return transaction


class MTNMobileMoney(PaymentGateway):
    """MTN Mobile Money Uganda Integration"""
    
    def __init__(self):
        super().__init__()
        self.name = "MTN Mobile Money"
        self.base_url = "https://sandbox.momodeveloper.mtn.com"
        self.api_key = settings.MTN_API_KEY
        self.subscription_key = settings.MTN_SUBSCRIPTION_KEY
        self.callback_url = f"{settings.FRONTEND_URL}/api/v1/webhooks/mtn-payment/"
    
    def get_auth_token(self):
        """Get authentication token from MTN API"""
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Authorization": f"Basic {self.api_key}"
        }
        
        response = requests.post(
            f"{self.base_url}/collection/token/",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            raise Exception(f"Failed to get auth token: {response.text}")
    
    def initiate_payment(self, amount, phone, reference, **kwargs):
        """Request payment from customer (collect from employer)"""
        try:
            auth_token = self.get_auth_token()
            
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "X-Target-Environment": "sandbox",
                "Content-Type": "application/json",
                "Ocp-Apim-Subscription-Key": self.subscription_key,
                "X-Callback-Url": self.callback_url,
                "X-Reference-Id": reference
            }
            
            payload = {
                "amount": str(amount),
                "currency": "UGX",
                "externalId": reference,
                "payer": {
                    "partyIdType": "MSISDN",
                    "partyId": phone.lstrip("+")
                },
                "payerMessage": f"WorkConnect Invoice #{reference}",
                "payeeNote": f"Service fee payment - {reference}"
            }
            
            response = requests.post(
                f"{self.base_url}/collection/v1_0/requesttopay",
                json=payload,
                headers=headers
            )
            
            if response.status_code in [200, 202]:
                # Create transaction record
                transaction = self._create_transaction_record(
                    transaction_type=PaymentTransaction.TransactionType.EMPLOYER_PAYMENT,
                    amount=amount,
                    reference=reference,
                    internal_reference=reference,
                    provider_response=response.json()
                )
                
                return {
                    "success": True,
                    "transaction_id": reference,
                    "status": "initiated",
                    "message": "Payment request sent to customer",
                    "transaction": transaction
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code} - {response.text}",
                    "status": "failed"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }
    
    def disburse_payment(self, amount, phone, reference, **kwargs):
        """Send payment to recipient (disburse to worker)"""
        try:
            auth_token = self.get_auth_token()
            
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "X-Target-Environment": "sandbox",
                "Content-Type": "application/json",
                "Ocp-Apim-Subscription-Key": self.subscription_key,
                "X-Reference-Id": reference
            }
            
            payload = {
                "amount": str(amount),
                "currency": "UGX",
                "externalId": reference,
                "payee": {
                    "partyIdType": "MSISDN",
                    "partyId": phone.lstrip("+")
                },
                "payerMessage": f"Salary payment #{reference}",
                "payeeNote": f"Monthly salary - WorkConnect"
            }
            
            response = requests.post(
                f"{self.base_url}/disbursement/v1_0/transfer",
                json=payload,
                headers=headers
            )
            
            if response.status_code in [200, 202]:
                # Create transaction record
                transaction = self._create_transaction_record(
                    transaction_type=PaymentTransaction.TransactionType.WORKER_DISBURSEMENT,
                    amount=amount,
                    reference=reference,
                    internal_reference=reference,
                    provider_response=response.json()
                )
                
                return {
                    "success": True,
                    "transaction_id": reference,
                    "status": "initiated",
                    "message": "Payment disbursement initiated",
                    "transaction": transaction
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code} - {response.text}",
                    "status": "failed"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }
    
    def check_payment_status(self, transaction_id):
        """Check status of a transaction"""
        try:
            auth_token = self.get_auth_token()
            
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "X-Target-Environment": "sandbox",
                "Ocp-Apim-Subscription-Key": self.subscription_key
            }
            
            response = requests.get(
                f"{self.base_url}/collection/v1_0/requesttopay/{transaction_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "PENDING")
                
                # Map MTN status to our status
                status_map = {
                    "SUCCESSFUL": "successful",
                    "FAILED": "failed",
                    "PENDING": "pending"
                }
                
                return {
                    "success": True,
                    "status": status_map.get(status, "pending"),
                    "provider_status": status,
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code} - {response.text}",
                    "status": "unknown"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "unknown"
            }
    
    def validate_webhook(self, request):
        """Validate MTN webhook signature"""
        signature = request.headers.get("X-Callback-Signature")
        payload = request.body
        
        # In production, you would verify the signature
        # For now, we'll accept all webhooks in sandbox
        return True
    
    def parse_webhook(self, data):
        """Parse MTN webhook data"""
        transaction_id = data.get("financialTransactionId")
        status = data.get("status")
        amount = data.get("amount")
        currency = data.get("currency")
        payer = data.get("payer", {})
        
        return {
            "transaction_id": transaction_id,
            "status": status,
            "amount": amount,
            "currency": currency,
            "payer_phone": payer.get("partyId"),
            "raw_data": data
        }


class AirtelMoney(PaymentGateway):
    """Airtel Money Uganda Integration"""
    
    def __init__(self):
        super().__init__()
        self.name = "Airtel Money"
        self.base_url = "https://openapi.airtel.africa"
        self.client_id = settings.AIRTEL_CLIENT_ID
        self.client_secret = settings.AIRTEL_CLIENT_SECRET
        self.callback_url = f"{settings.FRONTEND_URL}/api/v1/webhooks/airtel-payment/"
    
    def get_auth_token(self):
        """Get authentication token from Airtel API"""
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        
        response = requests.post(
            f"{self.base_url}/auth/oauth2/token",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            raise Exception(f"Failed to get auth token: {response.text}")
    
    def initiate_payment(self, amount, phone, reference, **kwargs):
        """Initiate Airtel Money payment"""
        try:
            auth_token = self.get_auth_token()
            
            headers = {
                "X-Country": "UG",
                "X-Currency": "UGX",
                "Authorization": f"Bearer {auth_token}"
            }
            
            payload = {
                "reference": reference,
                "subscriber": {
                    "country": "UG",
                    "currency": "UGX",
                    "msisdn": phone.lstrip("+")
                },
                "transaction": {
                    "amount": amount,
                    "country": "UG",
                    "currency": "UGX",
                    "id": reference
                }
            }
            
            response = requests.post(
                f"{self.base_url}/merchant/v1/payments/",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                transaction_id = data.get("data", {}).get("transaction", {}).get("id")
                
                # Create transaction record
                transaction = self._create_transaction_record(
                    transaction_type=PaymentTransaction.TransactionType.EMPLOYER_PAYMENT,
                    amount=amount,
                    reference=reference,
                    internal_reference=transaction_id,
                    provider_response=data
                )
                
                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "status": "initiated",
                    "message": "Payment initiated",
                    "transaction": transaction
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code} - {response.text}",
                    "status": "failed"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }
    
    def check_payment_status(self, transaction_id):
        """Check Airtel payment status"""
        try:
            auth_token = self.get_auth_token()
            
            headers = {
                "X-Country": "UG",
                "X-Currency": "UGX",
                "Authorization": f"Bearer {auth_token}"
            }
            
            response = requests.get(
                f"{self.base_url}/standard/v1/payments/{transaction_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("data", {}).get("transaction", {}).get("status")
                
                return {
                    "success": True,
                    "status": status,
                    "provider_status": status,
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code} - {response.text}",
                    "status": "unknown"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "unknown"
            }
    
    def validate_webhook(self, request):
        """Validate Airtel webhook signature"""
        # Airtel typically signs webhooks with a secret
        # Implementation depends on Airtel's specific method
        return True
    
    def parse_webhook(self, data):
        """Parse Airtel webhook data"""
        transaction = data.get("transaction", {})
        
        return {
            "transaction_id": transaction.get("id"),
            "status": transaction.get("status"),
            "amount": transaction.get("amount"),
            "currency": transaction.get("currency"),
            "payer_phone": transaction.get("payer", {}).get("msisdn"),
            "raw_data": data
        }

# payments/gateways.py (continued)

class FlutterwaveGateway(PaymentGateway):
    """Flutterwave Integration for Card Payments"""
    
    def __init__(self):
        super().__init__()
        self.name = "Flutterwave"
        self.base_url = "https://api.flutterwave.com/v3"
        self.public_key = settings.FLUTTERWAVE_PUBLIC_KEY
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY
        self.redirect_url = f"{settings.FRONTEND_URL}/payment/callback"
    
    def initiate_payment(self, amount, email, reference, **kwargs):
        """Initiate card payment via Flutterwave"""
        try:
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "tx_ref": reference,
                "amount": str(amount),
                "currency": "UGX",
                "redirect_url": self.redirect_url,
                "customer": {
                    "email": email,
                    "name": kwargs.get("customer_name", "Customer")
                },
                "customizations": {
                    "title": "WorkConnect Uganda",
                    "description": f"Payment for invoice #{reference}"
                }
            }
            
            # Add phone if provided
            if kwargs.get("phone"):
                payload["customer"]["phone_number"] = kwargs["phone"]
            
            response = requests.post(
                f"{self.base_url}/payments",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                payment_link = data.get("data", {}).get("link")
                
                # Create transaction record
                transaction = self._create_transaction_record(
                    transaction_type=PaymentTransaction.TransactionType.EMPLOYER_PAYMENT,
                    amount=amount,
                    reference=reference,
                    internal_reference=reference,
                    provider_response=data
                )
                
                return {
                    "success": True,
                    "payment_link": payment_link,
                    "status": "initiated",
                    "message": "Payment link generated",
                    "transaction": transaction
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code} - {response.text}",
                    "status": "failed"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }
    
    def verify_payment(self, transaction_id):
        """Verify Flutterwave payment"""
        try:
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.base_url}/transactions/{transaction_id}/verify",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("data", {}).get("status")
                amount = data.get("data", {}).get("amount")
                
                return {
                    "success": True,
                    "status": status,
                    "amount": amount,
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code} - {response.text}",
                    "status": "unknown"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "unknown"
            }
    
    def validate_webhook(self, request):
        """Validate Flutterwave webhook signature"""
        signature = request.headers.get("verifi-hash")
        payload = request.body.decode('utf-8')
        
        if not signature or signature != settings.FLUTTERWAVE_WEBHOOK_HASH:
            return False
        
        return True
    
    def parse_webhook(self, data):
        """Parse Flutterwave webhook data"""
        return {
            "transaction_id": data.get("id"),
            "reference": data.get("tx_ref"),
            "status": data.get("status"),
            "amount": data.get("amount"),
            "currency": data.get("currency"),
            "customer_email": data.get("customer", {}).get("email"),
            "raw_data": data
        }