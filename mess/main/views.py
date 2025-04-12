from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Like

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_likes_count(request):
    """
    Возвращает количество лайков, полученных текущим пользователем
    """
    likes_count = Like.objects.filter(to_user=request.user).count()
    return Response({'count': likes_count}) 