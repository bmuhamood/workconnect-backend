# ai/serializers.py
from rest_framework import serializers


class ChatbotRequestSerializer(serializers.Serializer):
    """Serializer for chatbot requests"""
    message = serializers.CharField(max_length=1000)
    conversation_history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=[]
    )
    context = serializers.CharField(required=False, default="")


class VoiceToTextSerializer(serializers.Serializer):
    """Serializer for voice-to-text requests"""
    audio_file = serializers.FileField()
    language = serializers.CharField(default='en-UG')
    job_category = serializers.CharField(required=False)
    experience_level = serializers.CharField(required=False, default='intermediate')


class OCRRequestSerializer(serializers.Serializer):
    """Serializer for OCR requests"""
    image_file = serializers.FileField()
    document_type = serializers.ChoiceField(
        choices=['national_id', 'passport', 'driver_license', 'other']
    )
    worker_id = serializers.UUIDField(required=False)


class InterviewQuestionsSerializer(serializers.Serializer):
    """Serializer for interview questions requests"""
    job_category = serializers.CharField()
    experience_level = serializers.CharField(default='intermediate')
    specific_skills = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=[]
    )
    number_of_questions = serializers.IntegerField(default=10, min_value=5, max_value=20)


class SentimentAnalysisSerializer(serializers.Serializer):
    """Serializer for sentiment analysis requests"""
    text = serializers.CharField()
    analyze_fake_review = serializers.BooleanField(default=False)


class SalaryRecommendationSerializer(serializers.Serializer):
    """Serializer for salary recommendation requests"""
    job_category = serializers.CharField()
    location = serializers.CharField()
    experience_years = serializers.IntegerField(min_value=0)
    skills = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=[]
    )
