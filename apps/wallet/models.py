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

    def has_active_subscription(self):
        """Check if HR profile has an active subscription with unlimited credits"""
        try:
            from apps.subscriptions.utils import has_unlimited_credits
            return has_unlimited_credits(self.hr_profile)
        except ImportError:
            return False

    def get_subscription_info(self):
        """Get subscription status information"""
        try:
            from apps.subscriptions.utils import get_subscription_status
            return get_subscription_status(self.hr_profile)
        except ImportError:
            return None

    def can_unlock(self, credits_required=10):
        """
        Check if user can unlock a profile
        First checks for active subscription with unlimited credits
        Then checks wallet balance
        """
        # Check if has active unlimited subscription
        if self.has_active_subscription():
            return True

        # Otherwise check wallet balance
        return self.balance >= credits_required

    def deduct_credits(self, amount):
        """
        Deduct credits from wallet
        If user has active unlimited subscription, don't deduct from balance
        Otherwise deduct from wallet balance
        """
        # Check for active unlimited subscription
        if self.has_active_subscription():
            # Track usage in subscription but don't deduct from wallet
            try:
                from apps.subscriptions.utils import get_active_subscription
                subscription = get_active_subscription(self.hr_profile)
                if subscription and subscription.plan.is_unlimited:
                    # For unlimited plans, just track in total_spent
                    self.total_spent += amount
                    self.save()
                    return True
                elif subscription:
                    # For limited subscription plans, use subscription credits
                    if subscription.use_credits(amount):
                        self.total_spent += amount
                        self.save()
                        return True
            except ImportError:
                pass

        # No subscription or subscription credits exhausted, use wallet balance
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