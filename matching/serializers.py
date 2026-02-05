# matching/serializers.py
from rest_framework import serializers
from matching.services import MatchingService


class MatchingRequestSerializer(serializers.Serializer):
    job_posting_id = serializers.UUIDField(required=False)
    job_category_id = serializers.UUIDField(required=False)
    required_skills = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    location_lat = serializers.FloatField(required=False)
    location_lng = serializers.FloatField(required=False)
    salary_max = serializers.IntegerField(required=False)
    experience_min_years = serializers.IntegerField(required=False)
    
    def validate(self, data):
        # Either job_posting_id OR other parameters are required
        if not data.get('job_posting_id') and not data.get('job_category_id'):
            raise serializers.ValidationError(
                "Either job_posting_id or job_category_id is required"
            )
        return data


class MatchResultSerializer(serializers.Serializer):
    worker_id = serializers.UUIDField()
    match_score = serializers.FloatField()
    profile = serializers.DictField()
    ai_insights = serializers.ListField(child=serializers.CharField())
    ai_recommendation = serializers.CharField()
