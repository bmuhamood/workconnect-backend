from django.utils import timezone
from datetime import date, timedelta
from contracts.models import Contract, ContractReplacement
from payments.models import PayrollCycle, EmployerInvoice


class ContractManager:
    """Service for managing contract lifecycle"""
    
    @staticmethod
    def activate_contract(contract):
        """Activate a contract"""
        if contract.status != Contract.ContractStatus.DRAFT:
            raise ValueError("Only draft contracts can be activated")
        
        if not contract.signed_by_employer or not contract.signed_by_worker:
            raise ValueError("Both parties must sign the contract before activation")
        
        contract.status = Contract.ContractStatus.TRIAL
        contract.activated_at = timezone.now()
        contract.save()
        
        # Create initial payroll entry
        ContractManager._create_initial_payroll_entry(contract)
        
        return contract
    
    @staticmethod
    def complete_trial(contract, passed=True, feedback=""):
        """Complete trial period"""
        if contract.status != Contract.ContractStatus.TRIAL:
            raise ValueError("Only contracts in trial can complete trial")
        
        if date.today() < contract.trial_end_date:
            raise ValueError("Trial period has not ended yet")
        
        contract.is_trial = False
        contract.trial_passed = passed
        contract.trial_feedback = feedback
        
        if passed:
            contract.status = Contract.ContractStatus.ACTIVE
        else:
            contract.status = Contract.ContractStatus.TERMINATED
            contract.completed_at = timezone.now()
        
        contract.save()
        
        # Update worker stats if trial passed
        if passed and contract.worker:
            contract.worker.total_placements += 1
            contract.worker.save()
        
        return contract
    
    @staticmethod
    def request_replacement(contract, reason, requested_by):
        """Request worker replacement during trial"""
        if not contract.can_request_replacement:
            raise ValueError("Cannot request replacement for this contract")
        
        # Create replacement request
        replacement = ContractReplacement.objects.create(
            original_contract=contract,
            original_worker=contract.worker,
            reason=reason,
            requested_by=requested_by,
            is_free_replacement=True,  # Free during trial
            status=ContractReplacement.ReplacementStatus.REQUESTED
        )
        
        # Update contract status
        contract.status = Contract.ContractStatus.TRIAL  # Keep in trial but mark for replacement
        contract.save()
        
        return replacement
    
    @staticmethod
    def approve_replacement(replacement, replacement_worker):
        """Approve replacement with new worker"""
        if replacement.status != ContractReplacement.ReplacementStatus.REQUESTED:
            raise ValueError("Only requested replacements can be approved")
        
        if replacement_worker.availability != 'available':
            raise ValueError("Replacement worker is not available")
        
        # Create new contract with replacement worker
        original_contract = replacement.original_contract
        new_contract = Contract.objects.create(
            employer=original_contract.employer,
            worker=replacement_worker,
            category=original_contract.category,
            contract_type=original_contract.contract_type,
            job_title=original_contract.job_title,
            job_description=original_contract.job_description,
            worker_salary_amount=original_contract.worker_salary_amount,
            service_fee_amount=original_contract.service_fee_amount,
            start_date=date.today(),
            trial_duration_days=original_contract.trial_duration_days,
            work_location=original_contract.work_location,
            work_hours_per_week=original_contract.work_hours_per_week,
            work_schedule=original_contract.work_schedule,
            created_by=replacement.requested_by
        )
        
        # Update replacement record
        replacement.replacement_worker = replacement_worker
        replacement.new_contract = new_contract
        replacement.status = ContractReplacement.ReplacementStatus.COMPLETED
        replacement.completed_at = timezone.now()
        replacement.save()
        
        # Terminate original contract
        original_contract.status = Contract.ContractStatus.TERMINATED
        original_contract.completed_at = timezone.now()
        original_contract.termination_reason = f"Replaced by {replacement_worker.first_name} {replacement_worker.last_name}"
        original_contract.save()
        
        # Update worker availability
        replacement_worker.availability = 'on_assignment'
        replacement_worker.save()
        
        return new_contract
    
    @staticmethod
    def terminate_contract(contract, reason, terminated_by):
        """Terminate a contract"""
        if contract.status not in [Contract.ContractStatus.ACTIVE, Contract.ContractStatus.TRIAL]:
            raise ValueError("Only active or trial contracts can be terminated")
        
        contract.status = Contract.ContractStatus.TERMINATED
        contract.termination_reason = reason
        contract.termination_initiated_by = terminated_by
        contract.completed_at = timezone.now()
        contract.save()
        
        # Update worker availability
        if contract.worker:
            contract.worker.availability = 'available'
            contract.worker.save()
        
        # Cancel any pending invoices
        ContractManager._cancel_pending_invoices(contract)
        
        return contract
    
    @staticmethod
    def _create_initial_payroll_entry(contract):
        """Create initial payroll entry for contract"""
        # This would be implemented when integrating with payments app
        pass
    
    @staticmethod
    def _cancel_pending_invoices(contract):
        """Cancel pending invoices for terminated contract"""
        # This would be implemented when integrating with payments app
        pass
    
    @staticmethod
    def check_trial_expirations():
        """Check and handle expired trial periods"""
        today = date.today()
        
        # Find contracts with expired trials
        expired_trials = Contract.objects.filter(
            status=Contract.ContractStatus.TRIAL,
            trial_end_date__lt=today,
            trial_passed__isnull=True
        )
        
        for contract in expired_trials:
            # Auto-complete trial as failed if no action taken
            contract.is_trial = False
            contract.trial_passed = False
            contract.status = Contract.ContractStatus.TERMINATED
            contract.completed_at = timezone.now()
            contract.trial_feedback = "Trial expired automatically - no feedback provided"
            contract.save()
            
            # Update worker availability
            if contract.worker:
                contract.worker.availability = 'available'
                contract.worker.save()
