import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from django.core.exceptions import ValidationError
from .managers import CustomUserManager


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField(unique=True) 
    phone = models.CharField(max_length=14)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    activation_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    objects = CustomUserManager()

    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_set',  
        blank=True,
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_set',  
        blank=True,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone']  

    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    accounts = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.full_name()}"
    

class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    balance = models.DecimalField(max_digits=30, decimal_places=2)
    
    def __str__(self):
        return f"{self.user} - {self.balance}"
    

class Investment(models.Model):
    # Updated investment type choices to match the plans
    GOLDEN_EAGLE = 'golden_eagle'
    GOLDEN_EVO = 'golden_evo'
    VIP_GOLDEN_EAGLE = 'vip_golden_eagle'
    VVIP_GOLDEN_EAGLE = 'vvip_golden_eagle'
    MASTER_PLAN = 'master_plan'

    INVESTMENT_CHOICES = [
        (GOLDEN_EAGLE, 'Golden Eagle Plan'),
        (GOLDEN_EVO, 'Golden Evo Eagle Global Plan'),
        (VIP_GOLDEN_EAGLE, 'VIP Golden Eagle Plan'),
        (VVIP_GOLDEN_EAGLE, 'VVIP Golden Eagle Global Plan'),
        (MASTER_PLAN, 'Golden Eagle Master Plan'),
    ]

    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    investment_type = models.CharField(max_length=50, choices=INVESTMENT_CHOICES)
    amount = models.DecimalField(max_digits=30, decimal_places=2)
    has_earned = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    date_invested = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Investment by {self.user.username} - {self.get_investment_type_display()} - Amount: {self.amount}"


class UserPayMentAccounts(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  
    name = models.CharField(max_length=5, blank=True, null=True)
    accunt = models.CharField(max_length=200, blank=True, null=True)
    network = models.CharField(max_length=5, blank=True, null=True)
    
    def __str__(self):
        return f"Coin: {self.name}, \nWallet Address: {self.accunt}, \nNetwork: {self.network}"


class Transaction(models.Model):
    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    TRANSACTION_TYPE_CHOICES = [
        ('deposit', 'Deposit'), 
        ('withdrawal', 'Withdrawal')
    ]
    investment = models.ForeignKey(Investment, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE_CHOICES, default='deposit')
    amount = models.DecimalField(max_digits=30, decimal_places=2)
    withdrawal_account = models.ForeignKey(UserPayMentAccounts, on_delete= models.CASCADE, null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=TRANSACTION_STATUS_CHOICES, default='pending')

    def save(self, *args, **kwargs):
        if self.pk:
            old_transaction = Transaction.objects.get(pk=self.pk)
            old_status = old_transaction.status
        else:
            old_status = None

        super().save(*args, **kwargs)

        if old_status != 'approved' and self.status == 'approved':
            try:
                wallet = Wallet.objects.get(user=self.user)
            except Wallet.DoesNotExist:
                raise ValidationError("Wallet does not exist for the user.")

            if self.transaction_type == 'deposit':
                pass
            elif self.transaction_type == 'withdrawal':
                if wallet.balance < self.amount:
                    raise ValidationError("Insufficient funds for withdrawal.")
                wallet.balance -= self.amount

            wallet.save()


    def __str__(self):
        return f"{self.transaction_type.capitalize()} of {self.amount} for {self.user} - Status: {self.status}"



class Earnings(models.Model):
    investment = models.ForeignKey(Investment, on_delete=models.DO_NOTHING)
    amount_earned = models.DecimalField(max_digits=30, decimal_places=2)
    date_earned = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        wallet = Wallet.objects.get(user=self.investment.user)

        if self.pk:
            old_earnings = Earnings.objects.get(pk=self.pk)
            old_amount = old_earnings.amount_earned
        else:
            old_amount = 0  

        difference = self.amount_earned - old_amount

        wallet.balance += difference
        wallet.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Earnings for {self.investment} - Amount Earned: {self.amount_earned}"
    
    

class PaymentMethod(models.Model):
    name = models.CharField(max_length=5, blank=True, null=True)
    wallet = models.CharField(max_length=200, blank=True, null=True)
    network = models.CharField(max_length=5, blank=True, null=True)
    
    def __str__(self):
        return f"Coin: {self.name}, \nWallet Address: {self.wallet}, \nNetwork: {self.network}"
    
    
class Referral(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=10, unique=True, blank=True)
    reward_amount = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = str(uuid.uuid4())[:10]  # Generate a unique referral code
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.owner.username} - Code: {self.code}'
    
    
class Testimonial(models.Model):
    img = models.URLField(max_length=255)
    quote = models.TextField()
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} - {self.role}"
    
    
class DepositComfirm(models.Model):
    wallet_credited = models.CharField(max_length=200)
    transaction_hash = models.CharField(max_length=300)
    
    def __str__(self):
        return f"{self.wallet_credited}"
    
    
    
    
class Bonus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount =  models.DecimalField(max_digits=10, decimal_places=2)
    date_added = models.DateTimeField(default=timezone.now)
    
    
    def __str__(self):
        return f"{self.user} {self.amount}"