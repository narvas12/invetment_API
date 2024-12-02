from django.urls import path


from .views import (
    ActivateUserView,
    AddEarningsAPIView,
    AdminLoginView,
    BonusAPIView,
    BulkPaymentMethodUpload,
    DashboardOverviewView,
    DepositComfirmAPIView,
    DepositTransactionListView,
    DepositTransactionStatusUpdateView,
    DepositTransactionView,
    EarningsListView,
    InvestmentListView,
    PendingDepositsView,
    PendingWithdrawalsView,
    TestimonialAPIView,
    UserLoginView, 
    UserLogoutView,
    UserPaymentAccountsView, 
    UserView,
    WithdrawalTransactionListView,
    WithdrawalTransactionStatusUpdateView,
    WithdrawalTransactionView
)


urlpatterns = [
    path('auth/login/', UserLoginView.as_view()),

    path('auth/register/', UserView.as_view()),
    path('users/', UserView.as_view()),
    path('user/<uuid:user_id>/', UserView.as_view()),
    
    path('auth/activate/<uuid:token>/', ActivateUserView.as_view()),
    path('auth/login/custom/', UserLoginView.as_view()),
    path('auth/logout/', UserLogoutView.as_view()),

    path('investments/', InvestmentListView.as_view()),
    
    path('transactions/deposits/', DepositTransactionListView.as_view()),
    path('transactions/deposits/add/', DepositTransactionView.as_view()),
    path('transactions/deposits/update/status/', DepositTransactionStatusUpdateView.as_view()),

    path('transactions/pending-deposits/', PendingDepositsView.as_view()),
    path('transactions/pending-withdrawals/', PendingWithdrawalsView.as_view()),

    # Withdrawal Endpoints
    path('transactions/withdrawals/', WithdrawalTransactionListView.as_view()),
    path('transactions/withdrawals/add/', WithdrawalTransactionView.as_view()),
    path('transactions/withdrawals/update/status/', WithdrawalTransactionStatusUpdateView.as_view()),

    # Earnings
    path('earnings/', EarningsListView.as_view()),
    path('earnings/add/', AddEarningsAPIView.as_view()),
    
    path('dashboard/overview/', DashboardOverviewView.as_view()),
    
    path('payment-methods/', BulkPaymentMethodUpload.as_view()),
    path('payment-methods/<int:id>/', BulkPaymentMethodUpload.as_view()),
    
    path('testimonials/', TestimonialAPIView.as_view()),  
    path('testimonials/<int:pk>/', TestimonialAPIView.as_view()),  
    
    path('deposits/', DepositComfirmAPIView.as_view()),               
    path('deposits/<int:deposit_id>/', DepositComfirmAPIView.as_view()),
    
    path('payment-accounts/', UserPaymentAccountsView.as_view()),  
    path('payment-accounts/add/', UserPaymentAccountsView.as_view()),  
    path('payment-accounts/<int:pk>/', UserPaymentAccountsView.as_view()), 
    
    path('bonuses/', BonusAPIView.as_view()),  
    path('bonuses/<int:id>/', BonusAPIView.as_view()), 

    path('admin/login/', AdminLoginView.as_view()),
]
