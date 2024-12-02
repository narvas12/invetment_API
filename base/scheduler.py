from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django.utils import timezone
from datetime import timedelta
from .models import Investment, Earnings, Wallet
from decimal import Decimal

def calculate_monthly_earnings():
    today = timezone.now().date()
    last_month = today.replace(day=1) - timedelta(days=1)
    thirty_days_ago = today - timedelta(days=30)

    investments = Investment.objects.filter(is_active=True, has_earned=False, date_invested__lte=thirty_days_ago)

    for investment in investments:

        if investment.investment_type == Investment.GOLDEN_EAGLE:
            percentage = Decimal('0.05')  
        elif investment.investment_type == Investment.GOLDEN_EVO:
            percentage = Decimal('0.07')  
        elif investment.investment_type == Investment.VIP_GOLDEN_EAGLE:
            percentage = Decimal('0.10')  
        elif investment.investment_type == Investment.VVIP_GOLDEN_EAGLE:
            percentage = Decimal('0.12')  
        elif investment.investment_type == Investment.MASTER_PLAN:
            percentage = Decimal('0.15')  
        else:
            continue  

        earnings_amount = investment.amount * percentage
        total_transfer = investment.amount + earnings_amount

        Earnings.objects.create(
            investment=investment,
            amount_earned=earnings_amount,
            date_earned=last_month
        )

        wallet, created = Wallet.objects.get_or_create(user=investment.user)
        wallet.balance += total_transfer
        wallet.save()

        investment.has_earned = True
        investment.is_active = False  
        investment.save()

        print(f"Earnings processed for {investment.user.email} - "
              f"{investment.get_investment_type_display()}: "
              f"Earnings: {earnings_amount}, Total transferred: {total_transfer}")


def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.add_job(
        calculate_monthly_earnings,
        trigger='cron',
        day='last',  
        hour=23,  
        minute=59, 
        name='calculate_monthly_earnings',
        jobstore='default'
    )

    register_events(scheduler)
    scheduler.start()
    print("Scheduler started and will run as per the cron schedule...")
