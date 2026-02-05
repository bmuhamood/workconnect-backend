from decimal import Decimal
from django.utils import timezone
from payments.models import ServiceFeeConfig


class FeeCalculator:
    """Calculate service fees based on configuration"""
    
    @staticmethod
    def calculate_service_fee(category_id, worker_salary):
        """
        Calculate WorkConnect service fee based on category configuration
        
        Args:
            category_id: UUID of job category
            worker_salary: Monthly salary in UGX
        
        Returns:
            Service fee amount in UGX
        """
        try:
            # Get active fee configuration for category
            config = ServiceFeeConfig.objects.get(
                category_id=category_id,
                is_active=True,
                effective_from__lte=timezone.now().date()
            )
            
            fee = 0
            
            if config.fee_type == ServiceFeeConfig.FeeCalculationType.FIXED_AMOUNT:
                fee = config.fixed_amount or 0
                
            elif config.fee_type == ServiceFeeConfig.FeeCalculationType.PERCENTAGE:
                if config.percentage:
                    fee = int(worker_salary * (Decimal(config.percentage) / Decimal(100)))
                else:
                    fee = 0
                
            elif config.fee_type == ServiceFeeConfig.FeeCalculationType.TIERED:
                fee = FeeCalculator._calculate_tiered_fee(config.tier_config, worker_salary)
            
            # Apply minimum and maximum limits
            if config.minimum_fee and fee < config.minimum_fee:
                fee = config.minimum_fee
            
            if config.maximum_fee and fee > config.maximum_fee:
                fee = config.maximum_fee
            
            return fee
            
        except ServiceFeeConfig.DoesNotExist:
            # Default fee: 25% of first month's salary, with minimum 100,000 UGX
            default_fee = int(worker_salary * 0.25)
            return max(default_fee, 100000)
    
    @staticmethod
    def _calculate_tiered_fee(tier_config, salary):
        """Calculate fee based on salary tiers"""
        if not tier_config:
            return 0
        
        try:
            # Parse tier config if it's a string
            if isinstance(tier_config, str):
                import json
                tiers = json.loads(tier_config)
            else:
                tiers = tier_config
            
            # Find appropriate tier
            for tier in tiers:
                min_salary = tier.get('min', 0)
                max_salary = tier.get('max', float('inf'))
                fee = tier.get('fee', 0)
                
                if min_salary <= salary <= max_salary:
                    return fee
            
            # If salary exceeds all tiers, use highest tier fee
            if tiers:
                return tiers[-1].get('fee', 0)
            
            return 0
            
        except Exception as e:
            print(f"Error calculating tiered fee: {e}")
            # Fallback to default calculation
            return int(salary * 0.25)
