import os
from io import BytesIO
from datetime import datetime
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import boto3
from botocore.exceptions import ClientError


class ContractDocumentGenerator:
    """Generate PDF contract documents"""
    
    def __init__(self, contract):
        self.contract = contract
        self.s3_client = None
        if settings.USE_S3:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
    
    def generate(self):
        """Generate PDF contract and upload to storage"""
        # Create PDF
        pdf_buffer = self._create_pdf()
        
        # Generate filename
        filename = f"contract_{self.contract.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Upload to storage
        if settings.USE_S3 and self.s3_client:
            file_url = self._upload_to_s3(pdf_buffer, filename)
        else:
            file_url = self._save_locally(pdf_buffer, filename)
        
        # Update contract with document URL
        self.contract.contract_document_url = file_url
        self.contract.save(update_fields=['contract_document_url'])
        
        return file_url
    
    def _create_pdf(self):
        """Create PDF document"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            alignment=1  # Center
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=6
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Build document
        story = []
        
        # Title
        story.append(Paragraph("WORK CONNECT UGANDA", title_style))
        story.append(Paragraph("EMPLOYMENT CONTRACT", title_style))
        story.append(Spacer(1, 20))
        
        # Contract Details
        story.append(Paragraph("1. CONTRACT DETAILS", heading_style))
        
        details_data = [
            ["Contract ID:", str(self.contract.id)],
            ["Job Title:", self.contract.job_title],
            ["Contract Type:", self.contract.get_contract_type_display()],
            ["Status:", self.contract.get_status_display()],
        ]
        
        details_table = Table(details_data, colWidths=[2*inch, 4*inch])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 12))
        
        # Parties
        story.append(Paragraph("2. PARTIES", heading_style))
        
        employer = self.contract.employer
        worker = self.contract.worker
        
        parties_data = [
            ["Employer:", f"{employer.first_name} {employer.last_name}"],
            ["Company:", employer.company_name or "Individual"],
            ["Address:", employer.address or "Not specified"],
            ["Phone:", employer.user.phone],
            ["Email:", employer.user.email],
            ["", ""],
            ["Worker:", f"{worker.first_name} {worker.last_name}"],
            ["ID Number:", worker.national_id or "Not provided"],
            ["Address:", f"{worker.city}, {worker.district or ''}"],
            ["Phone:", worker.user.phone],
            ["Email:", worker.user.email],
        ]
        
        parties_table = Table(parties_data, colWidths=[2*inch, 4*inch])
        parties_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(parties_table)
        story.append(Spacer(1, 12))
        
        # Financial Terms
        story.append(Paragraph("3. FINANCIAL TERMS", heading_style))
        
        financial_data = [
            ["Worker Salary:", f"UGX {self.contract.worker_salary_amount:,} per month"],
            ["Service Fee:", f"UGX {self.contract.service_fee_amount:,} per month"],
            ["Total Monthly Cost:", f"UGX {self.contract.total_monthly_cost:,} per month"],
            ["Payment Frequency:", self.contract.payment_frequency.title()],
        ]
        
        financial_table = Table(financial_data, colWidths=[2*inch, 4*inch])
        financial_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(financial_table)
        story.append(Spacer(1, 12))
        
        # Contract Dates
        story.append(Paragraph("4. CONTRACT DATES", heading_style))
        
        dates_data = [
            ["Start Date:", self.contract.start_date.strftime("%B %d, %Y")],
            ["Trial End Date:", self.contract.trial_end_date.strftime("%B %d, %Y") if self.contract.trial_end_date else "N/A"],
            ["Trial Duration:", f"{self.contract.trial_duration_days} days"],
            ["End Date:", self.contract.end_date.strftime("%B %d, %Y") if self.contract.end_date else "Open-ended"],
        ]
        
        dates_table = Table(dates_data, colWidths=[2*inch, 4*inch])
        dates_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(dates_table)
        story.append(Spacer(1, 12))
        
        # Work Details
        story.append(Paragraph("5. WORK DETAILS", heading_style))
        story.append(Paragraph(f"Work Location: {self.contract.work_location or 'Not specified'}", normal_style))
        story.append(Paragraph(f"Work Hours per Week: {self.contract.work_hours_per_week} hours", normal_style))
        
        # Work Schedule
        if self.contract.work_schedule:
            story.append(Paragraph("Work Schedule:", normal_style))
            try:
                schedule = self.contract.work_schedule
                if isinstance(schedule, str):
                    import json
                    schedule = json.loads(schedule)
                
                for day, time in schedule.items():
                    story.append(Paragraph(f"  {day.title()}: {time}", normal_style))
            except:
                story.append(Paragraph("  Schedule details available in digital format", normal_style))
        
        story.append(Spacer(1, 12))
        
        # Terms and Conditions
        story.append(Paragraph("6. TERMS AND CONDITIONS", heading_style))
        
        terms = [
            "This contract is governed by the laws of Uganda.",
            "Either party may terminate this contract with 30 days written notice.",
            "During the trial period, either party may terminate immediately without penalty.",
            "Worker salary is paid through WorkConnect Uganda's payroll system.",
            "The employer is responsible for providing a safe working environment.",
            "All disputes shall be resolved through arbitration in Kampala.",
        ]
        
        for i, term in enumerate(terms, 1):
            story.append(Paragraph(f"{i}. {term}", normal_style))
        
        story.append(Spacer(1, 20))
        
        # Signature Blocks
        story.append(Paragraph("SIGNATURES", heading_style))
        story.append(Spacer(1, 30))
        
        # Employer Signature
        employer_signature = [
            ["Employer Signature:", "_________________________"],
            ["Name:", f"{employer.first_name} {employer.last_name}"],
            ["Date:", "_________________________"],
        ]
        
        employer_table = Table(employer_signature, colWidths=[2*inch, 4*inch])
        employer_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(employer_table)
        story.append(Spacer(1, 40))
        
        # Worker Signature
        worker_signature = [
            ["Worker Signature:", "_________________________"],
            ["Name:", f"{worker.first_name} {worker.last_name}"],
            ["Date:", "_________________________"],
        ]
        
        worker_table = Table(worker_signature, colWidths=[2*inch, 4*inch])
        worker_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(worker_table)
        
        # Generate PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _upload_to_s3(self, file_content, filename):
        """Upload file to AWS S3"""
        try:
            folder = f"contracts/{self.contract.id}"
            key = f"{folder}/{filename}"
            
            self.s3_client.put_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=key,
                Body=file_content,
                ContentType='application/pdf',
                ACL='private'
            )
            
            # Generate URL
            file_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{key}"
            return file_url
            
        except ClientError as e:
            print(f"Error uploading to S3: {e}")
            raise
    
    def _save_locally(self, file_content, filename):
        """Save file locally (for development)"""
        contracts_dir = os.path.join(settings.MEDIA_ROOT, 'contracts', str(self.contract.id))
        os.makedirs(contracts_dir, exist_ok=True)
        
        filepath = os.path.join(contracts_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(file_content)
        
        return f"/media/contracts/{self.contract.id}/{filename}"
    
    def get_signed_url(self, expires_in=3600):
        """Get signed URL for document (expires in specified seconds)"""
        if not self.contract.contract_document_url or not settings.USE_S3:
            return None
        
        try:
            # Extract key from URL
            url = self.contract.contract_document_url
            key = url.split(f"{settings.AWS_S3_CUSTOM_DOMAIN}/")[1]
            
            # Generate signed URL
            signed_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': key
                },
                ExpiresIn=expires_in
            )
            
            return signed_url
            
        except Exception as e:
            print(f"Error generating signed URL: {e}")
            return None
