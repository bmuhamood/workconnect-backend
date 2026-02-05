# ai/services.py
import openai
import json
from django.conf import settings
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import vision
import logging

logger = logging.getLogger(__name__)


class AIService:
    """Base AI service class"""
    
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.google_credentials = settings.GOOGLE_CLOUD_CREDENTIALS
        
        if self.openai_api_key:
            openai.api_key = self.openai_api_key


class ChatbotService(AIService):
    """AI Chatbot service"""
    
    def get_response(self, user_message, conversation_history=None, context=None):
        """
        24/7 AI chatbot for customer support
        """
        system_prompt = """
        You are a helpful customer service assistant for WorkConnect Uganda,
        a domestic worker recruitment platform. 
        
        You can help with:
        - How to register as employer/worker
        - How the trial period works
        - Payment and pricing questions
        - Explaining service fees
        - How to request replacements
        - Platform features and usage
        
        Be friendly, professional, and concise. If you don't know something,
        offer to connect them with human support.
        
        Current context: {context}
        """
        
        messages = [
            {"role": "system", "content": system_prompt.format(context=context or "General inquiry")}
        ]
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Using GPT-3.5 for cost efficiency
                messages=messages,
                max_tokens=300,
                temperature=0.7,
                timeout=30
            )
            
            return {
                "success": True,
                "response": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return {
                "success": False,
                "response": "I apologize, but I'm having trouble processing your request. Please try again or contact our support team.",
                "error": str(e)
            }


class VoiceToTextService(AIService):
    """Voice-to-text service using Google Cloud Speech-to-Text"""
    
    def __init__(self):
        super().__init__()
        if self.google_credentials:
            self.client = speech.SpeechClient.from_service_account_json(
                self.google_credentials
            )
    
    def transcribe_audio(self, audio_content, language_code='en-UG'):
        """
        Convert voice recording to text
        """
        try:
            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=True,
                model='latest_long'
            )
            
            response = self.client.recognize(config=config, audio=audio)
            
            # Combine all transcripts
            transcript = ""
            for result in response.results:
                transcript += result.alternatives[0].transcript + " "
            
            return {
                "success": True,
                "transcript": transcript.strip(),
                "confidence": result.alternatives[0].confidence if result.alternatives else 0
            }
            
        except Exception as e:
            logger.error(f"Google Speech-to-Text error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "transcript": ""
            }
    
    def structure_job_posting(self, transcript):
        """
        Convert transcript to structured job posting using OpenAI
        """
        prompt = f"""
        Convert this voice transcript into a structured job posting for a domestic worker:
        
        Transcript: "{transcript}"
        
        Extract and return valid JSON with the following structure:
        {{
            "job_title": "string (e.g., 'Nanny for Infant', 'Housekeeper')",
            "category": "string (e.g., 'Childcare', 'Housekeeping')",
            "description": "string (detailed job description)",
            "requirements": ["string", "string"] (list of requirements),
            "salary_range": {{"min": number, "max": number}},
            "start_date": "string (e.g., 'Next week', '2024-02-01')",
            "work_schedule": "string (e.g., 'Monday to Friday, 8am-5pm')"
        }}
        
        If you cannot determine a value, use null.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            # Parse JSON response
            json_str = response.choices[0].message.content
            # Clean the response (remove markdown code blocks)
            json_str = json_str.replace('```json', '').replace('```', '').strip()
            
            structured_data = json.loads(json_str)
            
            return {
                "success": True,
                "structured_posting": structured_data,
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            logger.error(f"Error structuring job posting: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "structured_posting": None
            }


class OCRService(AIService):
    """OCR service for document verification"""
    
    def __init__(self):
        super().__init__()
        if self.google_credentials:
            self.client = vision.ImageAnnotatorClient.from_service_account_json(
                self.google_credentials
            )
    
    def extract_id_card_data(self, image_content):
        """
        Extract text from Ugandan National ID card
        """
        try:
            image = vision.Image(content=image_content)
            
            # Perform text detection
            response = self.client.text_detection(image=image)
            texts = response.text_annotations
            
            if not texts:
                return {
                    "success": False,
                    "error": "No text found in image"
                }
            
            full_text = texts[0].description
            
            # Extract specific fields using pattern matching
            extracted_data = self.parse_id_card_text(full_text)
            
            # Calculate confidence
            confidence = self.calculate_confidence(extracted_data)
            
            return {
                "success": True,
                "full_text": full_text,
                "extracted_data": extracted_data,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Google Vision API error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def parse_id_card_text(self, text):
        """Parse ID card text to extract structured data"""
        import re
        
        data = {
            "id_number": None,
            "surname": None,
            "given_names": None,
            "sex": None,
            "date_of_birth": None,
            "place_of_birth": None,
            "nationality": None
        }
        
        # Extract ID number (pattern: CF followed by 12 digits and 3 letters)
        id_pattern = r'[A-Z]{2}\d{12}[A-Z]{3}'
        id_match = re.search(id_pattern, text)
        if id_match:
            data["id_number"] = id_match.group(0)
        
        # Extract names (common patterns in Ugandan IDs)
        name_patterns = [
            r'SURNAME:\s*([A-Z\s]+)\n',
            r'Surname:\s*([A-Z\s]+)\n',
            r'([A-Z\s]+)\s+SURNAME'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["surname"] = match.group(1).strip()
                break
        
        # Extract given names
        given_name_patterns = [
            r'GIVEN NAMES?:\s*([A-Z\s]+)\n',
            r'Given names?:\s*([A-Z\s]+)\n',
            r'([A-Z\s]+)\s+GIVEN'
        ]
        
        for pattern in given_name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["given_names"] = match.group(1).strip()
                break
        
        # Extract sex
        sex_patterns = [
            r'SEX:\s*([MF])\b',
            r'Sex:\s*([MF])\b',
            r'\b([MF])\s+SEX\b'
        ]
        
        for pattern in sex_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["sex"] = match.group(1)
                break
        
        # Extract date of birth
        dob_patterns = [
            r'DATE OF BIRTH:\s*(\d{2}/\d{2}/\d{4})',
            r'Date of Birth:\s*(\d{2}/\d{2}/\d{4})',
            r'DOB:\s*(\d{2}/\d{2}/\d{4})',
            r'\b(\d{2}/\d{2}/\d{4})\b'
        ]
        
        for pattern in dob_patterns:
            match = re.search(pattern, text)
            if match:
                data["date_of_birth"] = match.group(1)
                break
        
        return data
    
    def calculate_confidence(self, data):
        """Calculate confidence score based on extracted data completeness"""
        required_fields = ['id_number', 'surname', 'given_names', 'date_of_birth']
        
        filled_fields = sum(1 for field in required_fields if data.get(field))
        confidence = (filled_fields / len(required_fields)) * 100
        
        return round(confidence, 2)


class InterviewQuestionService(AIService):
    """AI service for generating interview questions"""
    
    def generate_questions(self, job_category, experience_level, specific_skills=None):
        """
        Generate personalized interview questions
        """
        prompt = f"""
        Generate 10 interview questions for hiring a {job_category} 
        with {experience_level} experience level.
        
        Specific skills to assess: {', '.join(specific_skills or [])}
        
        Include:
        - 3 behavioral questions
        - 4 skill-specific questions
        - 2 scenario-based questions
        - 1 motivation question
        
        Format as JSON array with question, purpose, and category.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.7
            )
            
            # Parse JSON response
            json_str = response.choices[0].message.content
            json_str = json_str.replace('```json', '').replace('```', '').strip()
            
            questions = json.loads(json_str)
            
            return {
                "success": True,
                "questions": questions,
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            logger.error(f"Error generating interview questions: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "questions": []
            }