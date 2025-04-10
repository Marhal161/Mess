from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..models import Interest
from ..serializers.InterestSerializer import InterestSerializer

class InterestListView(APIView):
    def get(self, request):
        interests = Interest.objects.all()
        serializer = InterestSerializer(interests, many=True, context={'request': request})
        return Response(serializer.data)