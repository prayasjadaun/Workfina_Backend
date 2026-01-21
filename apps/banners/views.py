from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Banner, RecruiterBanner
from .serializers import BannerSerializer, RecruiterBannerSerializer

class ActiveBannerView(APIView):
    def get(self, request):
        banner = Banner.objects.filter(is_active=True).first()
        if not banner:
            return Response(None)
        serializer = BannerSerializer(banner, context={'request': request})
        return Response(serializer.data)


class ActiveRecruiterBannerView(APIView):
    def get(self, request):
        banners = RecruiterBanner.objects.filter(is_active=True)
        if not banners.exists():
            return Response([])
        serializer = RecruiterBannerSerializer(banners, many=True, context={'request': request})
        return Response(serializer.data)
