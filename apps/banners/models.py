from django.db import models

class Banner(models.Model):
    title = models.CharField(max_length=200)
    button_text = models.CharField(max_length=50)
    image = models.ImageField(upload_to='banners/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class RecruiterBanner(models.Model):
    TEXT_ALIGN_CHOICES = [
        ('left', 'Left'),
        ('center', 'Center'),
        ('right', 'Right'),
    ]

    FONT_WEIGHT_CHOICES = [
        ('300', 'Light'),
        ('400', 'Regular'),
        ('500', 'Medium'),
        ('600', 'Semi Bold'),
        ('700', 'Bold'),
    ]

    heading = models.CharField(max_length=200, blank=True, null=True)
    subheading = models.CharField(max_length=300, blank=True, null=True)
    image = models.ImageField(upload_to='recruiter_banners/')
    height = models.PositiveIntegerField(default=250, help_text='Banner height in pixels')

    # Heading Styling
    heading_font_size = models.PositiveIntegerField(default=18, help_text='Font size in sp')
    heading_color = models.CharField(max_length=9, default='#FFFFFF', help_text='Hex color code (e.g., #FFFFFF)')
    heading_font_weight = models.CharField(max_length=3, choices=FONT_WEIGHT_CHOICES, default='600')

    # Subheading Styling
    subheading_font_size = models.PositiveIntegerField(default=14, help_text='Font size in sp')
    subheading_color = models.CharField(max_length=9, default='#FFFFFF', help_text='Hex color code (e.g., #FFFFFF)')
    subheading_font_weight = models.CharField(max_length=3, choices=FONT_WEIGHT_CHOICES, default='400')

    # Text Alignment
    text_align = models.CharField(max_length=10, choices=TEXT_ALIGN_CHOICES, default='left')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Recruiter Banner'
        verbose_name_plural = 'Recruiter Banners'
        ordering = ['-created_at']

    def __str__(self):
        return self.heading or f"Banner {self.id}"
