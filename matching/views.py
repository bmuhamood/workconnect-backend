# matching/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from matching.serializers import MatchingRequestSerializer, MatchResultSerializer
from matching.services import MatchingService
from job_postings.models import JobPosting
from users.models import WorkerProfile
from users.permissions import IsEmployer


class MatchingViewSet(viewsets.ViewSet):
    """ViewSet for AI-powered matching"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'], permission_classes=[IsEmployer])
    def find_workers(self, request):
        """Find matching workers for job requirements"""
        serializer = MatchingRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        matching_service = MatchingService()
        
        if data.get('job_posting_id'):
            # Find matches for existing job posting
            try:
                job_posting = JobPosting.objects.get(
                    id=data['job_posting_id'],
                    employer=request.user.employerprofile
                )
            except JobPosting.DoesNotExist:
                return Response(
                    {"error": "Job posting not found or you don't have permission"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            matches = matching_service.find_matching_workers(job_posting, limit=20)
        
        else:
            # Find matches based on search criteria
            # Create a temporary job posting object for matching
            from job_postings.models import JobPosting
            job_posting = JobPosting(
                title=f"Search: {data.get('required_skills', [''])[0] if data.get('required_skills') else 'Job'}",
                description="Temporary job for matching",
                salary_min=0,
                salary_max=data.get('salary_max', 1000000),
                location="",
                requirements=", ".join(data.get('required_skills', []))
            )
            
            # Apply additional filters
            base_query = WorkerProfile.objects.filter(
                availability='available',
                verification_status='verified'
            )
            
            if data.get('experience_min_years'):
                base_query = base_query.filter(
                    experience_years__gte=data['experience_min_years']
                )
            
            matches = []
            for worker in base_query[:100]:  # Limit initial query
                match_result = matching_service.calculate_match_score(worker, job_posting)
                
                if match_result['match_score'] >= 50:
                    matches.append({
                        'worker_id': worker.id,
                        'worker': worker,
                        'match_score': match_result['match_score'],
                        'breakdown': match_result['breakdown'],
                        'insights': match_result['insights'],
                        'recommendation': match_result['recommendation']
                    })
            
            matches.sort(key=lambda x: x['match_score'], reverse=True)
            matches = matches[:20]
        
        # Format response
        formatted_matches = []
        for match in matches:
            worker = match['worker']
            formatted_matches.append({
                'worker_id': str(worker.id),
                'name': worker.full_name,
                'profile_photo': worker.profile_photo_url,
                'experience_years': worker.experience_years,
                'rating': worker.rating_average,
                'trust_score': worker.trust_score,
                'match_score': match['match_score'],
                'ai_insights': match['insights'],
                'ai_recommendation': match['recommendation']
            })
        
        return Response({
            'total_matches': len(formatted_matches),
            'matches': formatted_matches
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsEmployer])
    def suggested_workers(self, request):
        """Get suggested workers based on employer's activity"""
        matching_service = MatchingService()
        
        # Get employer's most recent active job posting
        latest_job = JobPosting.objects.filter(
            employer=request.user.employerprofile,
            status=JobPosting.Status.ACTIVE
        ).order_by('-created_at').first()
        
        if not latest_job:
            return Response({"suggestions": [], "message": "No active job postings"})
        
        matches = matching_service.find_matching_workers(latest_job, limit=5)
        
        suggestions = []
        for match in matches:
            worker = match['worker']
            suggestions.append({
                'worker_id': str(worker.id),
                'name': worker.full_name,
                'match_score': match['match_score'],
                'recommendation': match['recommendation']
            })
        
        return Response({
            'job_posting': {
                'id': str(latest_job.id),
                'title': latest_job.title
            },
            'suggestions': suggestions
        })
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def explain_match(self, request, worker_id=None):
        """Explain why a worker is a good match"""
        if not worker_id:
            return Response(
                {"error": "worker_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            worker = WorkerProfile.objects.get(id=worker_id)
        except WorkerProfile.DoesNotExist:
            return Response(
                {"error": "Worker not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get relevant job posting for context
        job_posting_id = request.query_params.get('job_posting_id')
        
        if job_posting_id:
            try:
                job_posting = JobPosting.objects.get(id=job_posting_id)
            except JobPosting.DoesNotExist:
                job_posting = None
        else:
            # Get employer's latest job or create generic one
            if request.user.role == 'employer':
                job_posting = JobPosting.objects.filter(
                    employer=request.user.employerprofile
                ).order_by('-created_at').first()
            else:
                job_posting = None
        
        matching_service = MatchingService()
        
        if job_posting:
            match_result = matching_service.calculate_match_score(worker, job_posting)
        else:
            # Create generic job for explanation
            generic_job = JobPosting(
                title="Generic Domestic Work",
                description="Looking for reliable domestic worker",
                salary_min=300000,
                salary_max=500000,
                location="Kampala",
                requirements="Experience, reliability, good references"
            )
            match_result = matching_service.calculate_match_score(worker, generic_job)
        
        return Response({
            'worker': {
                'id': str(worker.id),
                'name': worker.full_name,
                'experience_years': worker.experience_years,
                'rating': worker.rating_average,
                'verification_status': worker.verification_status
            },
            'match_score': match_result['match_score'],
            'score_breakdown': match_result['breakdown'],
            'detailed_insights': match_result['insights'],
            'recommendation': match_result['recommendation']
        })
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def find_jobs(self, request):
        """Find matching jobs for workers"""
        try:
            worker_profile = request.user.workerprofile
        except:
            return Response(
                {"error": "Worker profile not found"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        matching_service = MatchingService()
        matches = matching_service.find_matching_jobs(worker_profile, limit=20)
        
        formatted_matches = []
        for match in matches:
            job = match['job']
            formatted_matches.append({
                'job_id': str(job.id),
                'title': job.title,
                'employer': job.employer.company_name,
                'salary_min': job.salary_min,
                'salary_max': job.salary_max,
                'location': job.location,
                'match_score': match['match_score'],
                'ai_insights': match['insights'],
                'ai_recommendation': match['recommendation']
            })
        
        return Response({
            'total_matches': len(formatted_matches),
            'matches': formatted_matches
        })
