from django.core.mail import send_mail
from django.conf import settings

def send_otp_email(email, otp):
    subject = 'Workfina Email Verification'
    message = f'Your OTP is: {otp}'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]
    
    send_mail(subject, message, from_email, recipient_list)