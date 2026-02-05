# job_postings/serializers.py
from rest_framework import serializers
from job_postings.models import JobPosting, JobApplication
from users.serializers import EmployerProfileSerializer, WorkerProfileSerializer
from contracts.serializers import JobCategorySerializer
from matching.services import MatchingService


class JobPostingSerializer(serializers.ModelSerializer):
    employer = EmployerProfileSerializer(read_only=True)
    category = JobCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True)
    employer_name = serializers.CharField(source='employer.company_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = JobPosting
        fields = '__all__'
        read_only_fields = [
            'created_at', 'updated_at', 'published_at',
            'views_count', 'applications_count', 'employer'
        ]
    
    def validate(self, data):
        # Validate salary range
        salary_min = data.get('salary_min')
        salary_max = data.get('salary_max')
        
        if salary_min and salary_max:
            if salary_min > salary_max:
                raise serializers.ValidationError(
                    "Minimum salary cannot be greater than maximum salary"
                )
        
        return data


class JobApplicationSerializer(serializers.ModelSerializer):
    job_posting = JobPostingSerializer(read_only=True)
    job_posting_id = serializers.UUIDField(write_only=True)
    worker = WorkerProfileSerializer(read_only=True)
    worker_name = serializers.CharField(source='worker.full_name', read_only=True)
    job_title = serializers.CharField(source='job_posting.title', read_only=True)
    
    class Meta:
        model = JobApplication
        fields = '__all__'
        read_only_fields = [
            'applied_at', 'reviewed_at', 'worker',
            'ai_match_score', 'ai_recommendation'
        ]
    
    def validate(self, data):
        # Check if application already exists
        job_posting_id = data.get('job_posting_id')
        if job_posting_id and self.context['request'].user.workerprofile:
            if JobApplication.objects.filter(
                job_posting_id=job_posting_id,
                worker=self.context['request'].user.workerprofile
            ).exists():
                raise serializers.ValidationError(
                    "You have already applied for this job"
                )
        
        return data
    
    def create(self, validated_data):
        # Calculate AI match score
        worker = self.context['request'].user.workerprofile
        job_posting = JobPosting.objects.get(id=validated_data['job_posting_id'])
        
        matching_service = MatchingService()
        match_result = matching_service.calculate_match_score(worker, job_posting)
        
        validated_data['ai_match_score'] = match_result['match_score']
        validated_data['ai_recommendation'] = match_result['recommendation']
        validated_data['worker'] = worker
        
        return super().create(validated_data)


class JobPostingCreateSerializer(serializers.ModelSerializer):
    category_id = serializers.UUIDField()
    
    class Meta:
        model = JobPosting
        fields = [
            'title', 'description', 'requirements',
            'salary_min', 'salary_max', 'location',
            'work_schedule', 'start_date', 'category_id',
            'is_featured'
        ]