# matching/services.py
import math
from typing import List, Dict, Any
from django.db.models import Q
from job_postings.models import JobPosting, JobApplication
from users.models import WorkerProfile
from contracts.models import Contract, JobCategory


class MatchingService:
    """AI-powered matching service"""
    
    def __init__(self):
        self.weights = {
            'skills_match': 0.30,      # 30%
            'location': 0.20,          # 20%
            'experience': 0.15,        # 15%
            'salary_match': 0.10,      # 10%
            'availability': 0.10,      # 10%
            'rating': 0.10,            # 10%
            'verification': 0.05       # 5%
        }
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate Haversine distance between two points in kilometers"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        
        return distance
    
    def calculate_match_score(self, worker: WorkerProfile, job_posting: JobPosting) -> Dict[str, Any]:
        """Calculate match score between worker and job posting"""
        score = 0
        breakdown = {}
        
        # Skills Match (30%)
        if job_posting.requirements:
            required_skills = self.extract_skills_from_text(job_posting.requirements)
            worker_skills = [skill.skill_name for skill in worker.skills.all()]
            
            if required_skills:
                overlap = len(set(required_skills) & set(worker_skills))
                skills_score = (overlap / len(required_skills)) * 100
            else:
                skills_score = 50  # Neutral score if no specific skills required
        else:
            skills_score = 50
        
        score += skills_score * self.weights['skills_match']
        breakdown['skills_match'] = round(skills_score, 2)
        
        # Location Proximity (20%)
        if worker.location_lat and worker.location_lng and job_posting.location:
            # Parse location or use coordinates
            distance_km = self.calculate_distance(
                worker.location_lat, worker.location_lng,
                0.3476, 32.5825  # Default to Kampala coordinates
            )
            location_score = max(0, 1 - (distance_km / 20)) * 100  # 20km threshold
        else:
            location_score = 50
        
        score += location_score * self.weights['location']
        breakdown['location'] = round(location_score, 2)
        
        # Experience Match (15%)
        min_experience = self.extract_min_experience(job_posting.requirements)
        if min_experience > 0:
            exp_score = min(1, worker.experience_years / min_experience) * 100
        else:
            exp_score = 100 if worker.experience_years > 0 else 50
        
        score += exp_score * self.weights['experience']
        breakdown['experience'] = round(exp_score, 2)
        
        # Salary Compatibility (10%)
        salary_score = 0
        if worker.expected_salary_min and worker.expected_salary_max:
            if (worker.expected_salary_min <= job_posting.salary_max and
                worker.expected_salary_max >= job_posting.salary_min):
                salary_score = 100
        
        score += salary_score * self.weights['salary_match']
        breakdown['salary_match'] = round(salary_score, 2)
        
        # Availability (10%)
        avail_score = 100 if worker.availability == 'available' else 0
        score += avail_score * self.weights['availability']
        breakdown['availability'] = round(avail_score, 2)
        
        # Rating (10%)
        rating_score = (worker.rating_average / 5.0) * 100
        score += rating_score * self.weights['rating']
        breakdown['rating'] = round(rating_score, 2)
        
        # Verification Status (5%)
        verif_score = 100 if worker.verification_status == 'verified' else 0
        score += verif_score * self.weights['verification']
        breakdown['verification'] = round(verif_score, 2)
        
        total_score = round(score, 2)
        
        # Generate AI insights
        insights = self.generate_insights(worker, job_posting, breakdown, total_score)
        
        return {
            'match_score': total_score,
            'breakdown': breakdown,
            'insights': insights,
            'recommendation': self.generate_recommendation(total_score, insights)
        }
    
    def extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skills from text using simple keyword matching"""
        common_skills = [
            'cooking', 'cleaning', 'childcare', 'nanny', 'housekeeping',
            'gardening', 'driver', 'security', 'cook', 'cleaner',
            'first aid', 'cpr', 'elderly care', 'baby care', 'laundry',
            'ironing', 'shopping', 'meal preparation', 'pet care'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in common_skills:
            if skill in text_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def extract_min_experience(self, text: str) -> int:
        """Extract minimum experience requirement from text"""
        # Simple pattern matching for years of experience
        import re
        
        patterns = [
            r'(\d+)\s+years? experience',
            r'experience\s+of\s+(\d+)\s+years?',
            r'minimum\s+(\d+)\s+years?',
            r'at least\s+(\d+)\s+years?'
        ]
        
        if not text:
            return 0
        
        text_lower = text.lower()
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except:
                    continue
        
        return 0
    
    def generate_insights(self, worker: WorkerProfile, job_posting: JobPosting, 
                         breakdown: Dict[str, float], score: float) -> List[str]:
        """Generate human-readable insights about the match"""
        insights = []
        
        if breakdown['skills_match'] > 80:
            insights.append("Excellent skill match for the position")
        elif breakdown['skills_match'] > 60:
            insights.append("Good skill alignment")
        
        if breakdown['location'] > 80:
            insights.append("Located within convenient distance")
        elif breakdown['location'] < 30:
            insights.append("Consider location - may require relocation")
        
        if breakdown['experience'] > 80:
            insights.append("More than sufficient experience")
        elif breakdown['experience'] < 50:
            insights.append("Consider experience level for this role")
        
        if breakdown['salary_match'] == 100:
            insights.append("Salary expectations align with position")
        else:
            insights.append("Salary expectations may need discussion")
        
        if breakdown['verification'] == 100:
            insights.append("Fully verified and background checked")
        
        if worker.rating_average >= 4.5:
            insights.append("Highly rated by previous employers")
        elif worker.rating_average >= 4.0:
            insights.append("Well-reviewed by previous employers")
        
        return insights[:5]  # Return top 5 insights
    
    def generate_recommendation(self, score: float, insights: List[str]) -> str:
        """Generate AI recommendation based on match score"""
        if score >= 90:
            return "Highly Recommended - Excellent match across all criteria"
        elif score >= 80:
            return "Strongly Recommended - Very good match"
        elif score >= 70:
            return "Recommended - Good match with minor considerations"
        elif score >= 60:
            return "Consider - Moderate match, review details"
        elif score >= 50:
            return "Potential Match - Some alignment, needs evaluation"
        else:
            return "Limited Match - Significant differences to consider"
    
    def find_matching_workers(self, job_posting: JobPosting, limit: int = 20) -> List[Dict]:
        """Find matching workers for a job posting"""
        # Basic filtering
        base_query = WorkerProfile.objects.filter(
            availability='available',
            verification_status='verified'
        )
        
        # Filter by category if specified
        if job_posting.category:
            base_query = base_query.filter(
                skills__category=job_posting.category
            ).distinct()
        
        # Calculate scores for each worker
        matches = []
        for worker in base_query[:100]:  # Limit initial query
            match_result = self.calculate_match_score(worker, job_posting)
            
            if match_result['match_score'] >= 50:  # Only include decent matches
                matches.append({
                    'worker_id': worker.id,
                    'worker': worker,
                    'match_score': match_result['match_score'],
                    'breakdown': match_result['breakdown'],
                    'insights': match_result['insights'],
                    'recommendation': match_result['recommendation']
                })
        
        # Sort by match score and limit results
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        return matches[:limit]
    
    def find_matching_jobs(self, worker: WorkerProfile, limit: int = 20) -> List[Dict]:
        """Find matching job postings for a worker"""
        # Basic filtering
        base_query = JobPosting.objects.filter(
            status='active',
            expires_at__gt=timezone.now()
        )
        
        # Filter by category based on worker skills
        worker_categories = worker.skills.values_list('category', flat=True).distinct()
        if worker_categories:
            base_query = base_query.filter(category__in=worker_categories)
        
        # Calculate scores for each job
        matches = []
        for job in base_query[:100]:  # Limit initial query
            match_result = self.calculate_match_score(worker, job)
            
            if match_result['match_score'] >= 50:
                matches.append({
                    'job_id': job.id,
                    'job': job,
                    'match_score': match_result['match_score'],
                    'breakdown': match_result['breakdown'],
                    'insights': match_result['insights'],
                    'recommendation': match_result['recommendation']
                })
        
        # Sort by match score and limit results
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        return matches[:limit]