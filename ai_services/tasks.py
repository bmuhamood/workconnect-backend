# ai_services/tasks.py
from celery import shared_task
from django.utils import timezone
import logging
from ai_services.services import (
    ChatbotService, VoiceToTextService, OCRService,
    InterviewQuestionService, SentimentAnalyzer
)

logger = logging.getLogger(__name__)


@shared_task
def process_worker_documents_with_ai(worker_id):
    """Process worker documents with AI OCR"""
    from users.models import WorkerProfile
    
    try:
        worker = WorkerProfile.objects.get(id=worker_id)
        ocr_service = OCRService()
        
        # Process each document
        for document in worker.documents.all():
            if document.document_type in ['national_id', 'passport']:
                # Process document with OCR
                # This would depend on your actual implementation
                pass
        
        # Mark as processed
        worker.ai_processed = True
        worker.save(update_fields=['ai_processed'])
        
        return {
            "success": True,
            "worker_id": str(worker_id),
            "documents_processed": worker.documents.count()
        }
        
    except WorkerProfile.DoesNotExist:
        logger.error(f"Worker not found: {worker_id}")
        return {"success": False, "error": "Worker not found"}
    except Exception as e:
        logger.error(f"Error processing documents: {str(e)}")
        return {"success": False, "error": str(e)}


@shared_task
def generate_ai_recommendations_for_job(job_posting_id):
    """Generate AI recommendations for a job posting"""
    from job_postings.models import JobPosting
    from matching.services import MatchingService
    
    try:
        job_posting = JobPosting.objects.get(id=job_posting_id)
        matching_service = MatchingService()
        
        # Find matching workers
        matches = matching_service.find_matching_workers(job_posting, limit=20)
        
        # Store recommendations in job posting
        job_posting.ai_recommendations = {
            "generated_at": timezone.now().isoformat(),
            "total_matches": len(matches),
            "top_matches": [
                {
                    "worker_id": str(match['worker'].id),
                    "match_score": match['match_score'],
                    "recommendation": match['recommendation']
                }
                for match in matches[:5]  # Top 5 matches
            ]
        }
        job_posting.save()
        
        return {
            "success": True,
            "job_posting_id": str(job_posting_id),
            "matches_found": len(matches)
        }
        
    except JobPosting.DoesNotExist:
        logger.error(f"Job posting not found: {job_posting_id}")
        return {"success": False, "error": "Job posting not found"}
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        return {"success": False, "error": str(e)}


@shared_task
def analyze_contract_with_ai(contract_id):
    """Analyze contract with AI"""
    from contracts.models import Contract
    
    try:
        contract = Contract.objects.get(id=contract_id)
        
        # Analyze contract terms, duration, etc.
        # This would depend on your AI implementation
        
        contract.ai_analysis = {
            "analyzed_at": timezone.now().isoformat(),
            "risk_score": 0,  # Placeholder
            "recommendations": []  # Placeholder
        }
        contract.save()
        
        return {
            "success": True,
            "contract_id": str(contract_id)
        }
        
    except Contract.DoesNotExist:
        logger.error(f"Contract not found: {contract_id}")
        return {"success": False, "error": "Contract not found"}
    except Exception as e:
        logger.error(f"Error analyzing contract: {str(e)}")
        return {"success": False, "error": str(e)}


@shared_task
def analyze_review_sentiment(review_id):
    """Analyze review sentiment with AI"""
    from reviews.models import Review
    from ai_services.services import SentimentAnalyzer
    
    try:
        review = Review.objects.get(id=review_id)
        sentiment_analyzer = SentimentAnalyzer()
        
        # Analyze sentiment
        analysis = sentiment_analyzer.analyze(
            text=review.comment,
            analyze_fake_review=True
        )
        
        # Store analysis results
        review.sentiment_analysis = analysis
        review.save()
        
        # Flag suspicious reviews
        if analysis.get('fake_review_detection', {}).get('is_suspicious'):
            review.is_flagged = True
            review.flagged_reason = "AI detected suspicious patterns"
            review.save()
            
            # Notify admin
            from notifications.tasks import send_notification_task
            from users.models import User
            
            admins = User.objects.filter(role__in=['admin', 'super_admin'])
            for admin in admins:
                send_notification_task.delay(
                    user_id=str(admin.id),
                    notification_type='review',
                    title='Suspicious Review Detected',
                    message=f'AI detected a potentially fake review from {review.reviewer.get_full_name()}',
                    action_url=f'/admin/reviews/{review.id}',
                    action_text='Review',
                    data={
                        'review_id': str(review.id),
                        'reviewer_id': str(review.reviewer.id),
                        'confidence': analysis.get('confidence', 0)
                    }
                )
        
        return {
            "success": True,
            "review_id": str(review_id),
            "sentiment": analysis.get('sentiment'),
            "is_suspicious": analysis.get('fake_review_detection', {}).get('is_suspicious', False)
        }
        
    except Review.DoesNotExist:
        logger.error(f"Review not found: {review_id}")
        return {"success": False, "error": "Review not found"}
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        return {"success": False, "error": str(e)}


@shared_task
def generate_interview_questions_batch(job_category, experience_level, count=10):
    """Generate interview questions in batch"""
    interview_service = InterviewQuestionService()
    
    result = interview_service.generate_questions(
        job_category=job_category,
        experience_level=experience_level,
        count=count
    )
    
    return {
        "success": result.get('success', False),
        "job_category": job_category,
        "experience_level": experience_level,
        "questions_generated": len(result.get('questions', [])),
        "tokens_used": result.get('tokens_used', 0)
    }


@shared_task
def batch_process_documents_with_ocr(document_ids):
    """Batch process documents with OCR"""
    from documents.models import
from documents.models import WorkerDocument
    from ai_services.services import OCRService
    
    ocr_service = OCRService()
    results = []
    
    for doc_id in document_ids:
        try:
            document = WorkerDocument.objects.get(id=doc_id)
            
            # Process with OCR
            ocr_result = ocr_service.extract_data(document)
            
            document.ai_ocr_result = ocr_result
            document.save()
            
            results.append({
                "document_id": str(doc_id),
                "success": True,
                "confidence": ocr_result.get('confidence', 0)
            })
            
        except WorkerDocument.DoesNotExist:
            results.append({
                "document_id": str(doc_id),
                "success": False,
                "error": "Document not found"
            })
        except Exception as e:
            results.append({
                "document_id": str(doc_id),
                "success": False,
                "error": str(e)
            })
    
    return {
        "total": len(document_ids),
        "processed": sum(1 for r in results if r['success']),
        "failed": sum(1 for r in results if not r['success']),
        "results": results
    }


@shared_task
def cleanup_ai_cache():
    """Clean up AI cache and temporary files"""
    import os
    import shutil
    from django.conf import settings
    
    cache_dir = os.path.join(settings.MEDIA_ROOT, 'ai_cache')
    
    if os.path.exists(cache_dir):
        # Remove files older than 7 days
        import time
        now = time.time()
        
        for filename in os.listdir(cache_dir):
            filepath = os.path.join(cache_dir, filename)
            if os.path.isfile(filepath):
                file_age = now - os.path.getmtime(filepath)
                if file_age > 7 * 24 * 3600:  # 7 days in seconds
                    os.remove(filepath)
        
        logger.info("AI cache cleaned up")
    
    return {"success": True, "cache_dir": cache_dir}