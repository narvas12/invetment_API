from django.contrib import admin
from .models import DepositComfirm, PaymentMethod, Testimonial, User, UserProfile, Wallet, Investment, Transaction, Earnings

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'is_active', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_active',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_of_birth', 'address', 'created_at')
    search_fields = ('user__email',)

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')
    search_fields = ('user__email',)

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'investment_type', 'amount', 'is_active', 'date_invested')
    search_fields = ('user__email',)
    list_filter = ('investment_type', 'is_active')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'amount', 'date', 'status')
    search_fields = ('transaction_type',)
    list_filter = ('status', 'transaction_type')

@admin.register(Earnings)
class EarningsAdmin(admin.ModelAdmin):
    list_display = ('investment', 'amount_earned', 'date_earned')
    search_fields = ('investment__user__email',)



@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'wallet', 'network')
    search_fields = ('name', 'network')
    list_filter = ('network',)
    
    
@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['quote', 'name', 'role']
    

@admin.register(DepositComfirm)
class DepositComfirmAdmin(admin.ModelAdmin):
    list_display =['wallet_credited', 'transaction_hash']
    