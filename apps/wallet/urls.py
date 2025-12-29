from django.urls import path
from .views import wallet_balance, recharge_wallet, TransactionHistoryView

urlpatterns = [
    path('balance/', wallet_balance, name='wallet-balance'),
    path('recharge/', recharge_wallet, name='recharge-wallet'),
    path('transactions/', TransactionHistoryView.as_view(), name='transaction-history'),
]