from django.db import models

class Banner(models.Model):
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

    # Basic Content (Optional)
    title = models.CharField(max_length=200, blank=True, null=True, help_text='Banner heading (optional)')
    button_text = models.CharField(max_length=50, blank=True, null=True, help_text='Button text (optional)')
    image = models.ImageField(upload_to='banners/')

    # Banner Dimensions
    height = models.PositiveIntegerField(default=170, help_text='Banner height in pixels')

    # Title Styling
    title_font_size = models.PositiveIntegerField(default=15, help_text='Title font size in sp')
    title_color = models.CharField(max_length=9, default='#FFFFFF', help_text='Hex color code (e.g., #FFFFFF)')
    title_font_weight = models.CharField(max_length=3, choices=FONT_WEIGHT_CHOICES, default='600')

    # Button Styling
    button_bg_color = models.CharField(max_length=9, default='#FFFFFF', help_text='Button background color')
    button_text_color = models.CharField(max_length=9, default='#000000', help_text='Button text color')
    button_font_size = models.PositiveIntegerField(default=13, help_text='Button font size in sp')
    button_font_weight = models.CharField(max_length=3, choices=FONT_WEIGHT_CHOICES, default='600')
    button_border_radius = models.PositiveIntegerField(default=20, help_text='Button border radius in pixels')
    button_padding_horizontal = models.PositiveIntegerField(default=20, help_text='Button horizontal padding')
    button_padding_vertical = models.PositiveIntegerField(default=10, help_text='Button vertical padding')

    # Gradient Overlay Settings
    gradient_start_color = models.CharField(max_length=9, default='#000000', help_text='Gradient start color')
    gradient_start_opacity = models.DecimalField(max_digits=3, decimal_places=2, default=0.7, help_text='Opacity 0.0 to 1.0')
    gradient_end_color = models.CharField(max_length=9, default='#000000', help_text='Gradient end color')
    gradient_end_opacity = models.DecimalField(max_digits=3, decimal_places=2, default=0.15, help_text='Opacity 0.0 to 1.0')

    # Content Alignment
    content_alignment = models.CharField(max_length=10, choices=TEXT_ALIGN_CHOICES, default='left', help_text='Content alignment')
    content_padding = models.PositiveIntegerField(default=20, help_text='Content padding in pixels')

    # Border Radius
    border_radius = models.PositiveIntegerField(default=16, help_text='Banner border radius in pixels')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Candidate Banner'
        verbose_name_plural = 'Candidate Banners'
        ordering = ['-created_at']

    def __str__(self):
        return self.title if self.title else f"Banner {self.id}"


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
