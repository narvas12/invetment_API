import uuid
from rest_framework import serializers
from django.core.mail import send_mail
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction


from .models import (
    Bonus,
    DepositComfirm,
    PaymentMethod,
    Referral,
    Testimonial,
    User, 
    Investment, 
    Earnings,
    UserPayMentAccounts, 
    Transaction,
    Wallet
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','first_name', 'last_name', 'email', 'phone', 'avatar', 'is_active', "is_staff"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'avatar', 'is_active', 'password', 'referral_code']

    def validate(self, attrs):
        if User.objects.filter(email=attrs.get('email')).exists():
            raise serializers.ValidationError({'email': 'A user with this email already exists.'})

        if User.objects.filter(phone=attrs.get('phone')).exists():
            raise serializers.ValidationError({'phone': 'A user with this phone number already exists.'})

        return attrs

    def create(self, validated_data):
        referral_code = validated_data.pop('referral_code', None)
        validated_data['username'] = validated_data['email']

        # Create the user instance
        user = User(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            phone=validated_data['phone'],
            avatar=validated_data.get('avatar', None),
            username=validated_data['username'],
            is_active=True,
            activation_token=uuid.uuid4()
        )

        # Activation link (for your reference, printing to console)
        activation_link = f"http://127.0.0.1:8000/api/v1/activate/{user.activation_token}/"
        print(activation_link)

        user.set_password(validated_data['password'])
        user.save()

        Wallet.objects.create(user=user, balance=0)

        Referral.objects.create(owner=user)

        if referral_code:
            try:
                referral = Referral.objects.get(code=referral_code)

                referrer_wallet = Wallet.objects.get(user=referral.owner)
                referrer_wallet.balance += referral.reward_amount
                referrer_wallet.save()
            except Referral.DoesNotExist:
                pass  

        return user

    def send_activation_email(self, user):
        activation_link = f"http://127.0.0.1:8000/api/v1/activate/{user.activation_token}/"
        print(activation_link)
        send_mail(
            'Activate Your Account',
            f'Please activate your account by clicking this link: {activation_link}',
            'from@example.com',
            [user.email],
            fail_silently=False,
        )
        
        
class UserLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        identifier = attrs.get('identifier')
        password = attrs.get('password')

        if not identifier or not password:
            raise serializers.ValidationError("Identifier and password are required.")

        return attrs
    
class AdminLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        identifier = attrs.get('identifier')
        password = attrs.get('password')

        if not identifier or not password:
            raise serializers.ValidationError("Identifier and password are required.")

        return attrs



class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['user', 'balance']
        read_only_fields = ['user']

class InvestmentDetailSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.full_name', read_only=True) 

    class Meta:
        model = Investment
        fields = ['id', 'user', 'investment_type', 'amount', 'is_active', 'date_invested']
        
class InvestmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Investment
        fields = ['user', 'investment_type', 'amount', 'is_active', 'date_invested']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'transaction_type', 'amount', 'date', 'status']
        read_only_fields = ['date', 'status']
        
    
    
class DepositTransactionSerializer(serializers.ModelSerializer):
    investment_type = serializers.ChoiceField(choices=Investment.INVESTMENT_CHOICES, write_only=True)

    class Meta:
        model = Transaction
        fields = ['transaction_type', 'amount', 'investment_type']
        read_only_fields = ['transaction_type']

    def validate(self, data):
        investment_type = data.get('investment_type')
        amount = data.get('amount')

        limits = {
            Investment.GOLDEN_EAGLE: (100, 1000),
            Investment.GOLDEN_EVO: (1000, 5000),
            Investment.VIP_GOLDEN_EAGLE: (5000, 15000),
            Investment.VVIP_GOLDEN_EAGLE: (15000, 50000),
            Investment.MASTER_PLAN: (50000, float('inf'))
        }

        if investment_type in limits:
            min_amount, max_amount = limits[investment_type]
            if not (min_amount <= amount <= max_amount):
                max_limit = 'no limit' if max_amount == float('inf') else f"${max_amount}"
                raise ValidationError({
                    "amount": f"The deposit for {investment_type} must be between ${min_amount} and {max_limit}."
                })

        return data


    def create(self, validated_data):
        user = self.context['request'].user
        investment_type = validated_data.pop('investment_type')
        amount = validated_data['amount']

        with db_transaction.atomic():  # Ensures consistency in case of failures
            # Create the investment
            investment = Investment.objects.create(
                user=user,
                investment_type=investment_type,
                amount=amount,
            )

            # Create the transaction and link it to the investment
            transaction = Transaction.objects.create(
                user=user,
                transaction_type='deposit',
                amount=amount,
                status='pending',
                investment=investment  # Link the investment to the transaction
            )

        return transaction



class WithdrawalTransactionSerializer(serializers.ModelSerializer):
    withdrawal_account = serializers.PrimaryKeyRelatedField(
        queryset=UserPayMentAccounts.objects.none(),
        write_only=True
    )

    class Meta:
        model = Transaction
        fields = ['transaction_type', 'amount', 'withdrawal_account']
        read_only_fields = ['transaction_type']

    def __init__(self, *args, **kwargs):
        user = kwargs['context']['request'].user
        super().__init__(*args, **kwargs)
        self.fields['withdrawal_account'].queryset = UserPayMentAccounts.objects.filter(user=user)

    def create(self, validated_data):
        user = self.context['request'].user  
        amount = validated_data['amount']
        withdrawal_account = validated_data['withdrawal_account']

        wallet = Wallet.objects.select_for_update().get(user=user)

        if wallet.balance < amount:
            raise serializers.ValidationError("Insufficient funds for withdrawal.")

        wallet.balance -= amount
        wallet.save()

        transaction = Transaction.objects.create(
            user=user,  
            transaction_type='withdrawal',
            amount=amount,
            status='pending',
            withdrawal_account=withdrawal_account
        )
        return transaction


class InvestmentActivationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Investment
        fields = ['id', 'is_active']

    def activate_investment(self, investment):
        investment.is_active = True
        investment.save()
    
    
class TransactionStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'status']
        read_only_fields = ['transaction_type', 'amount', 'date']

    def validate_status(self, value):
        if value not in ['approved', 'rejected']:
            raise serializers.ValidationError("Status must be either 'approved' or 'rejected'.")
        return value

    def update(self, instance, validated_data):
        previous_status = instance.status
        new_status = validated_data.get('status')

        if new_status == 'approved' and previous_status != 'approved' and instance.transaction_type == 'deposit':

            if instance.investment:
                instance.investment.is_active = True  
                instance.investment.save()

        instance = super().update(instance, validated_data)
        return instance


    
class EarningsSerializer(serializers.ModelSerializer):
    date_earned = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    class Meta:
        model = Earnings
        fields = ['id', 'investment', 'amount_earned', 'date_earned']
        read_only_fields = ['date_earned']  
        
        
class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['name', 'wallet', 'network']
        
        
class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = '__all__' 
        
        
class DepositComfirmSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositComfirm
        fields = ['id', 'wallet_credited', 'transaction_hash']
        
        
class UserPaymentAccountsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPayMentAccounts
        fields = ['id', 'name', 'accunt', 'network']
        read_only_fields = ['id']

    def validate_accunt(self, value):
        if not value:
            raise serializers.ValidationError("Account cannot be blank.")
        return value
    
    
    
class BonusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bonus
        fields = ['user', 'amount']

    def validate_amount(self, value):

        try:
            amount = float(value)
            if amount <= 0:
                raise serializers.ValidationError("Amount must be greater than zero.")
        except ValueError:
            raise serializers.ValidationError("Invalid amount. It must be a number.")
        return value