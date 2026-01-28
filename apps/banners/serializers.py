from rest_framework import serializers
from .models import Banner, RecruiterBanner

class BannerSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = [
            'id', 'title', 'button_text', 'image', 'height',
            'title_font_size', 'title_color', 'title_font_weight',
            'button_bg_color', 'button_text_color', 'button_font_size',
            'button_font_weight', 'button_border_radius',
            'button_padding_horizontal', 'button_padding_vertical',
            'gradient_start_color', 'gradient_start_opacity',
            'gradient_end_color', 'gradient_end_opacity',
            'content_alignment', 'content_padding', 'border_radius'
        ]

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
