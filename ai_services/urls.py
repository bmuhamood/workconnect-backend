# ai/urls.py
from django.urls import path
from ai import views

urlpatterns = [
    path('chatbot/', views.ChatbotView.as_view(), name='ai-chatbot'),
    path('voice-to-text/', views.VoiceToTextView.as_view(), name='voice-to-text'),
    path('ocr/', views.OCRView.as_view(), name='ai-ocr'),
    path('interview-questions/', views.InterviewQuestionsView.as_view(), name='interview-questions'),
    path('sentiment-analysis/', views.SentimentAnalysisView.as_view(), name='sentiment-analysis'),
    path('salary-recommendation/', views.SalaryRecommendationView.as_view(), name='salary-recommendation'),
]
