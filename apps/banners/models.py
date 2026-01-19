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
    heading = models.CharField(max_length=200, blank=True, null=True)
    subheading = models.CharField(max_length=300, blank=True, null=True)
    image = models.ImageField(upload_to='recruiter_banners/')
    height = models.PositiveIntegerField(default=250, help_text='Banner height in pixels')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Recruiter Banner'
        verbose_name_plural = 'Recruiter Banners'
        ordering = ['-created_at']

    def __str__(self):
        return self.heading or f"Banner {self.id}"
