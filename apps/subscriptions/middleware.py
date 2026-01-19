from django.utils import timezone
from django.core.cache import cache
from .utils import check_expiring_subscriptions, expire_old_subscriptions


class SubscriptionCheckMiddleware:
    """
    Middleware to automatically check subscriptions once per day
    Uses cache to ensure it only runs once every 24 hours
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if we've already run today
        cache_key = f'subscription_check_{timezone.now().date()}'

        if not cache.get(cache_key):
            try:
                # Run subscription checks
                expire_old_subscriptions()
                check_expiring_subscriptions()

                # Mark as done for today (cache for 24 hours)
                cache.set(cache_key, True, 60 * 60 * 24)
            except Exception:
                # Silent fail - don't break the request
                pass

        response = self.get_response(request)
        return response
