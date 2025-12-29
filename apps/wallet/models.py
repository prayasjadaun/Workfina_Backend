from django.db import models
from apps.recruiters.models import HRProfile

class Wallet(models.Model):
    hr_profile = models.OneToOneField(HRProfile, on_delete=models.CASCADE)
    balance = models.PositiveIntegerField(default=0)
    total_spent = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.hr_profile} - Balance: {self.balance}"
        
    def can_unlock(self, credits_required=10):
        return self.balance >= credits_required
        
    def deduct_credits(self, amount):
        if self.balance >= amount:
            self.balance -= amount
            self.total_spent += amount
            self.save()
            return True
        return False

class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('RECHARGE', 'Credit Recharge'),
        ('UNLOCK', 'Profile Unlock'),
        ('REFUND', 'Refund'),
    ]
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    credits_added = models.PositiveIntegerField(default=0)
    credits_used = models.PositiveIntegerField(default=0)
    reference_id = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.wallet.hr_profile} - {self.transaction_type}"