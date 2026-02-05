# analytics/serializers.py
from rest_framework import serializers
from analytics.models import PlatformMetric, UserActivityLog


class PlatformMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformMetric
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class UserActivityLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    ip_address = serializers.IPAddressField(
        protocol='both',  # Accepts both IPv4 and IPv6
        allow_blank=True,
        allow_null=True,
        required=False
    )
    
    class Meta:
        model = UserActivityLog
        fields = '__all__'
        read_only_fields = ['created_at']

class DateRangeSerializer(serializers.Serializer):
    """Serializer for date range queries"""
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    
    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError(
                "Start date must be before end date"
            )
        
        # Limit date range to 90 days
        delta = data['end_date'] - data['start_date']
        if delta.days > 90:
            raise serializers.ValidationError(
                "Date range cannot exceed 90 days"
            )
        
        return data


class MetricsSummarySerializer(serializers.Serializer):
    """Serializer for metrics summary"""
    period = serializers.CharField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_users = serializers.IntegerField()
    active_contracts = serializers.IntegerField()
    growth_rate = serializers.FloatField()
    conversion_rate = serializers.FloatField()
