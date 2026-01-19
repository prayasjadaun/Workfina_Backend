from rest_framework import serializers
from .models import Banner, RecruiterBanner

class BannerSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = ['id', 'title', 'button_text', 'image']

    def get_image(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.image.url)


class RecruiterBannerSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = RecruiterBanner
        fields = [
            'id', 'heading', 'subheading', 'image', 'height',
            'heading_font_size', 'heading_color', 'heading_font_weight',
            'subheading_font_size', 'subheading_color', 'subheading_font_weight',
            'text_align'
        ]

    def get_image(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.image.url)
