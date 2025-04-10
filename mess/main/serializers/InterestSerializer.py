from rest_framework import serializers
from ..models import Interest

class InterestSerializer(serializers.ModelSerializer):
    icon = serializers.SerializerMethodField()
    
    class Meta:
        model = Interest
        fields = ['id', 'name', 'description', 'icon']
    
    def get_icon(self, obj):
        if obj.icon and hasattr(obj.icon, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.icon.url)
            return obj.icon.url
        return None