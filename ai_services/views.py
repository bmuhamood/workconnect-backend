# ai/views.py
from rest_framework import views, status, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
import json

from ai.serializers import (
    ChatbotRequestSerializer, VoiceToTextSerializer,
    OCRRequestSerializer, InterviewQuestionsSerializer,
    SentimentAnalysisSerializer, SalaryRecommendationSerializer
)
from ai.services import (
    ChatbotService, VoiceToTextService, OCRService,
    InterviewQuestionService
)
from users.permissions import IsEmployer, IsWorker, IsAdmin


class ChatbotView(views.APIView):
    """AI Chatbot endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChatbotRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        chatbot_service = ChatbotService()
        result = chatbot_service.get_response(
            user_message=data['message'],
            conversation_history=data.get('conversation_history', []),
            context=data.get('context', '')
        )
        
        if result['success']:
            return Response({
                "response": result['response'],
                "conversation_id": str(request.user.id),  # Using user ID for conversation tracking
                "tokens_used": result.get('tokens_used', 0)
            })
        else:
            return Response(
                {"error": result.get('error', 'Chatbot service unavailable')},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class VoiceToTextView(views.APIView):
    """Voice-to-text conversion endpoint"""
    permission_classes = [permissions.IsAuthenticated, IsEmployer]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        serializer = VoiceToTextSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Read audio file
        audio_file = data['audio_file']
        audio_content = audio_file.read()
        
        # Transcribe audio
        voice_service = VoiceToTextService()
        transcript_result = voice_service.transcribe_audio(
            audio_content=audio_content,
            language_code=data['language']
        )
        
        if not transcript_result['success']:
            return Response(
                {"error": transcript_result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Structure job posting if requested
        if data.get('job_category'):
            structured_result = voice_service.structure_job_posting(
                transcript_result['transcript']
            )
            
            if structured_result['success']:
                return Response({
                    "transcript": transcript_result['transcript'],
                    "structured_posting": structured_result['structured_posting'],
                    "confidence": transcript_result['confidence'],
                    "tokens_used": structured_result.get('tokens_used', 0)
                })
            else:
                return Response({
                    "transcript": transcript_result['transcript'],
                    "error": "Could not structure job posting",
                    "confidence": transcript_result['confidence']
                })
        
        return Response({
            "transcript": transcript_result['transcript'],
            "confidence": transcript_result['confidence']
        })


class OCRView(views.APIView):
    """OCR for document verification endpoint"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        serializer = OCRRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Read image file
        image_file = data['image_file']
        image_content = image_file.read()
        
        # Extract data using OCR
        ocr_service = OCRService()
        result = ocr_service.extract_id_card_data(image_content)
        
        if not result['success']:
            return Response(
                {"error": result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response_data = {
            "document_type": data['document_type'],
            "extracted_data": result['extracted_data'],
            "confidence": result['confidence'],
            "full_text": result.get('full_text', '')
        }
        
        # Link to worker if provided
        if data.get('worker_id'):
            from users.models import WorkerProfile
            try:
                worker = WorkerProfile.objects.get(id=data['worker_id'])
                
                # Auto-fill worker data if confidence is high
                if result['confidence'] > 80:
                    extracted = result['extracted_data']
                    
                    if extracted.get('id_number'):
                        worker.national_id = extracted['id_number']
                    
                    if extracted.get('date_of_birth'):
                        # Parse date format
                        from datetime import datetime
                        try:
                            dob = datetime.strptime(extracted['date_of_birth'], '%d/%m/%Y')
                            worker.date_of_birth = dob.date()
                        except:
                            pass
                    
                    worker.save()
                    
                    response_data['auto_filled'] = True
                    response_data['worker_updated'] = {
                        'id': str(worker.id),
                        'name': worker.full_name
                    }
                    
            except WorkerProfile.DoesNotExist:
                pass
        
        return Response(response_data)


class InterviewQuestionsView(views.APIView):
    """AI interview questions generator endpoint"""
    permission_classes = [permissions.IsAuthenticated, IsEmployer]
    
    def post(self, request):
        serializer = InterviewQuestionsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        interview_service = InterviewQuestionService()
        result = interview_service.generate_questions(
            job_category=data['job_category'],
            experience_level=data['experience_level'],
            specific_skills=data.get('specific_skills', [])
        )
        
        if result['success']:
            return Response({
                "questions": result['questions'],
                "tokens_used": result.get('tokens_used', 0),
                "count": len(result['questions'])
            })
        else:
            return Response(
                {"error": result.get('error', 'Failed to generate questions')},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class SentimentAnalysisView(views.APIView):
    """Sentiment analysis endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = SentimentAnalysisSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Simple sentiment analysis (can be enhanced with AI)
        text = data['text']
        
        # Basic sentiment analysis
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful',
                         'happy', 'pleased', 'satisfied', 'professional', 'reliable']
        negative_words = ['bad', 'terrible', 'awful', 'poor', 'disappointed',
                         'unhappy', 'late', 'rude', 'unprofessional']
        
        positive_count = sum(1 for word in positive_words if word in text.lower())
        negative_count = sum(1 for word in negative_words if word in text.lower())
        
        sentiment = "neutral"
        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        
        # Fake review detection (simple rules)
        is_suspicious = False
        red_flags = {}
        
        if data.get('analyze_fake_review'):
            red_flags = {
                'too_short': len(text.split()) < 10,
                'all_caps': text.isupper(),
                'excessive_punctuation': text.count('!') > 3 or text.count('?') > 3,
                'generic_phrases': any(phrase in text.lower() for phrase in [
                    'best ever', 'amazing', 'perfect in every way',
                    'worst ever', 'terrible experience'
                ]),
                'no_specifics': len([w for w in text.split() if len(w) > 5]) < 3
            }
            
            is_suspicious = sum(red_flags.values()) >= 2
        
        return Response({
            "sentiment": sentiment,
            "confidence": min(100, max(0, abs(positive_count - negative_count) * 20)),
            "analysis": {
                "positive_words_found": positive_count,
                "negative_words_found": negative_count,
                "word_count": len(text.split()),
                "character_count": len(text)
            },
            "fake_review_detection": {
                "is_suspicious": is_suspicious,
                "red_flags": red_flags,
                "recommendation": "Flag for review" if is_suspicious else "Looks genuine"
            }
        })


class SalaryRecommendationView(views.APIView):
    """Salary recommendation endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = SalaryRecommendationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Get historical data for recommendations
        from contracts.models import Contract
        
        similar_contracts = Contract.objects.filter(
            category__name=data['job_category'],
            status__in=['completed', 'active']
        )
        
        if data.get('location'):
            # Simple location filtering
            similar_contracts = similar_contracts.filter(
                work_location__icontains=data['location']
            )
        
        if similar_contracts.exists():
            # Calculate statistics
            from django.db.models import Avg, Min, Max
            
            stats = similar_contracts.aggregate(
                avg_salary=Avg('worker_salary_amount'),
                min_salary=Min('worker_salary_amount'),
                max_salary=Max('worker_salary_amount'),
                count=Count('id')
            )
            
            # Adjust based on experience
            base_salary = stats['avg_salary'] or 300000
            experience_multiplier = min(2.0, 1.0 + (data['experience_years'] * 0.1))
            
            # Adjust based on skills
            skill_bonus = len(data.get('skills', [])) * 50000
            
            recommended_min = int((base_salary * 0.8 * experience_multiplier) + skill_bonus)
            recommended_max = int((base_salary * 1.2 * experience_multiplier) + skill_bonus)
            
            return Response({
                "recommendation": {
                    "minimum_fair": recommended_min,
                    "average_market": int((recommended_min + recommended_max) / 2),
                    "maximum_competitive": recommended_max
                },
                "market_data": {
                    "sample_size": stats['count'],
                    "historical_average": stats['avg_salary'],
                    "historical_minimum": stats['min_salary'],
                    "historical_maximum": stats['max_salary']
                },
                "factors_considered": {
                    "experience_years": data['experience_years'],
                    "skill_count": len(data.get('skills', [])),
                    "location": data['location']
                }
            })
        
        else:
            # Default recommendations based on category
            category_defaults = {
                'nanny': {'min': 300000, 'avg': 400000, 'max': 600000},
                'housekeeper': {'min': 250000, 'avg': 350000, 'max': 500000},
                'gardener': {'min': 200000, 'avg': 300000, 'max': 450000},
                'driver': {'min': 400000, 'avg': 500000, 'max': 800000},
                'cook': {'min': 350000, 'avg': 450000, 'max': 700000}
            }
            
            defaults = category_defaults.get(
                data['job_category'].lower(),
                {'min': 250000, 'avg': 350000, 'max': 500000}
            )
            
            return Response({
                "recommendation": defaults,
                "market_data": {
                    "sample_size": 0,
                    "note": "Insufficient historical data, using category defaults"
                }
            })
