from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Banner
from .serializers import BannerSerializer

class ActiveBannerView(APIView):
    def get(self, request):
        banner = Banner.objects.filter(is_active=True).first()
        if not banner:
            return Response(None)
        serializer = BannerSerializer(banner, context={'request': request})
        return Response(serializer.data)
