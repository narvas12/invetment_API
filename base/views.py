from venv import logger
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db import models
from .managers import EmailNotificationManager
from .models import Bonus, DepositComfirm, Earnings, Investment, PaymentMethod, Referral, Testimonial, Transaction, User, UserPayMentAccounts, Wallet
from django.shortcuts import get_object_or_404
from django.db import transaction as db_transaction
from django.db.models import F, Value, DecimalField

from .serializers import (
    AdminLoginSerializer,
    BonusSerializer,
    DepositComfirmSerializer,
    DepositTransactionSerializer,
    EarningsSerializer,
    InvestmentDetailSerializer,
    PaymentMethodSerializer,
    TestimonialSerializer,
    TransactionSerializer,
    TransactionStatusUpdateSerializer,
    UserLoginSerializer,
    UserPaymentAccountsSerializer,
    UserRegistrationSerializer, 
    UserSerializer,
    WithdrawalTransactionSerializer
)


class UserView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id=None):
        if user_id:
            try:
                user = User.objects.get(pk=user_id)
                serializer = UserSerializer(user)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            users = User.objects.all()
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            EmailNotificationManager.send_welcome_email(user)
            return Response({'message': 'User created successfully.', 'user_id': user.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, user_id):
        self.permission_classes = [IsAuthenticated]
        self.check_permissions(request)

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserRegistrationSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'User updated successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        self.permission_classes = [IsAuthenticated]
        self.check_permissions(request)

        try:
            user = User.objects.get(pk=user_id)
            user.delete()
            return Response({'message': 'User deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)




class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # Validate the input data

        identifier = serializer.validated_data['identifier']
        password = serializer.validated_data['password']

        try:
            # Check if identifier is an email or phone number
            if '@' in identifier:
                user = User.objects.get(email=identifier)
            else:
                user = User.objects.get(phone=identifier)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Verify password
        if user.check_password(password):
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Serialize the user data
            user_data = UserSerializer(user).data

            # Return tokens and user data
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user_data,  # Include serialized user data
            }, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid credentials.'}, status=status.HTTP_400_BAD_REQUEST)



class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  

        identifier = serializer.validated_data['identifier']
        password = serializer.validated_data['password']

        try:
            if '@' in identifier:
                user = User.objects.get(email=identifier)
            else:
                user = User.objects.get(phone=identifier)
        except User.DoesNotExist:
            return Response({'error': 'Admin user not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user.check_password(password) and user.is_staff: 
            refresh = RefreshToken.for_user(user)

            user_data = UserSerializer(user).data

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user_data,  
            }, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid credentials or not an admin user.'}, status=status.HTTP_400_BAD_REQUEST)


class UserLogoutView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        try:
            RefreshToken(data['refresh']).blacklist() 
            return Response(status=205)
        except Exception as e:
            return Response(status=400)



class ActivateUserView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            user = User.objects.get(activation_token=token)
            user.is_active = True
            user.activation_token = None
            user.save()
            return Response({"message": "Your account has been activated!"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Invalid activation link."}, status=status.HTTP_400_BAD_REQUEST)
        

class InvestmentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:  
            investments = Investment.objects.all()
        else:
            investments = Investment.objects.filter(user=request.user)

        serializer = InvestmentDetailSerializer(investments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class DepositTransactionView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = DepositTransactionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                with db_transaction.atomic():  
                    transaction = serializer.save()

                user = request.user
                investment_type = serializer.validated_data['investment_type']

                # Send email notification
                EmailNotificationManager.send_transaction_initiation_email(
                    user=user,
                    transaction_type='deposit',
                    amount=transaction.amount,
                    transaction=transaction
                )

                return Response(serializer.data, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.error(f"Transaction processing failed: {str(e)}", exc_info=True)
                return Response(
                    {"error": "An error occurred while processing your transaction.", "details": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class WithdrawalTransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = WithdrawalTransactionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            transaction = serializer.save()
            user = request.user
            
            withdrawal_account = transaction.withdrawal_account
            
            EmailNotificationManager.send_transaction_initiation_email(
                user=user,
                transaction_type='withdrawal',
                amount=transaction.amount,
                transaction=transaction,
                withdrawal_account=withdrawal_account  
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



    
class DepositTransactionStatusUpdateView(APIView):
    """
    API endpoint to update the status of a deposit transaction.
    """
    def patch(self, request, *args, **kwargs):
        transaction_id = request.data.get('transaction_id')
        
        if not transaction_id:
            return Response({"detail": "Transaction ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            transaction = Transaction.objects.get(id=transaction_id, transaction_type='deposit')
        except Transaction.DoesNotExist:
            return Response({"detail": "Transaction not found or is not a deposit transaction."}, status=status.HTTP_404_NOT_FOUND)

        serializer = TransactionStatusUpdateSerializer(transaction, data=request.data, partial=True)
        
        if serializer.is_valid():
            updated_transaction = serializer.save()

            # Send email notification for the transaction status update
            EmailNotificationManager.send_transaction_status_email(
                user=transaction.user,
                transaction_type='deposit',
                amount=transaction.amount,
                status=updated_transaction.status  
            )

            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class WithdrawalTransactionStatusUpdateView(APIView):
    """
    API endpoint to update the status of a withdrawal transaction.
    """
    def patch(self, request, *args, **kwargs):
        transaction_id = request.data.get('transaction_id')  # Get transaction_id from the payload

        if not transaction_id:
            return Response({"detail": "Transaction ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transaction = Transaction.objects.get(id=transaction_id, transaction_type='withdrawal')
        except Transaction.DoesNotExist:
            return Response({"detail": "Transaction not found or is not a withdrawal transaction."}, status=status.HTTP_404_NOT_FOUND)

        serializer = TransactionStatusUpdateSerializer(transaction, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            EmailNotificationManager.send_transaction_status_email(
                user=transaction.user,  
                transaction_type='withdrawal',
                amount=transaction.amount,
                status=serializer.validated_data['status']
            )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PendingDepositsView(APIView):
    """
    View to list all pending deposit transactions.
    """
    permission_classes = [IsAuthenticated]  

    def get(self, request, *args, **kwargs):

        pending_deposits = Transaction.objects.filter(
            transaction_type='deposit', 
            status='pending'
        )
        print(pending_deposits)  # To check the output
        serializer = TransactionSerializer(pending_deposits, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PendingWithdrawalsView(APIView):
    """
    View to list all pending withdrawal transactions.
    """
    permission_classes = [IsAuthenticated]  

    def get(self, request, *args, **kwargs):

        pending_withdrawals = Transaction.objects.filter(
            transaction_type='withdrawal', 
            status='pending'
        )
        serializer = TransactionSerializer(pending_withdrawals, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class AddEarningsAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = EarningsSerializer(data=request.data)
        if serializer.is_valid():
            investment_id = request.data.get('investment')
            
            try:
                investment = Investment.objects.get(id=investment_id)
            except Investment.DoesNotExist:
                return Response({"error": "Investment not found."}, status=status.HTTP_404_NOT_FOUND)
            
            if not investment.is_active:
                return Response({"error": "Cannot add earnings to inactive investment."}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    
class DepositTransactionListView(APIView):
    """
    API to list all deposit transactions for the authenticated user
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        deposits = Transaction.objects.filter(transaction_type='deposit', user=request.user) 
        serializer = TransactionSerializer(deposits, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WithdrawalTransactionListView(APIView):
    """
    API to list all withdrawal transactions for the authenticated user
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):

        withdrawals = Transaction.objects.filter(transaction_type='withdrawal', user=request.user)
        serializer = TransactionSerializer(withdrawals, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
class EarningsListView(APIView):
    """
    API to list earnings for the authenticated user or for admins.
    """
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            earnings = Earnings.objects.filter(investment__user=request.user)
            serializer = EarningsSerializer(earnings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            earnings = Earnings.objects.all()
            serializer = EarningsSerializer(earnings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        
        
class DashboardOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        wallet = Wallet.objects.get(user=user)
        wallet_balance = wallet.balance

        investments = Investment.objects.filter(user=user)
        total_investment = investments.aggregate(total=models.Sum('amount'))['total'] or 0
        active_investment = investments.filter(is_active=True).aggregate(total=models.Sum('amount'))['total'] or 0

        total_earnings = Earnings.objects.filter(investment__user=user).aggregate(total=models.Sum('amount_earned'))['total'] or 0

        referral_rewards = Referral.objects.filter(owner=user)
        referral_earnings = referral_rewards.aggregate(total=models.Sum('reward_amount'))['total'] or 0

        referral = Referral.objects.filter(owner=user).first()
        referral_code = referral.code if referral else None

        total_deposits = Transaction.objects.filter(user=user, transaction_type='deposit', status='approved').aggregate(total=models.Sum('amount'))['total'] or 0
        total_withdrawals = Transaction.objects.filter(user=user, transaction_type='withdrawal', status='approved').aggregate(total=models.Sum('amount'))['total'] or 0

        referral_link = f"{referral_code}" if referral_code else None

        total_bonus = Bonus.objects.filter(user=user).annotate(amount_cast=F('amount')).aggregate(total=models.Sum('amount_cast'))['total'] or 0

        overview_data = {
            'wallet_balance': wallet_balance,
            'active_investment': active_investment,
            'total_earnings': total_earnings,
            'referral_earnings': referral_earnings,
            'referral_link': referral_link,  
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'total_bonus': total_bonus,
        }

        return Response(overview_data)


    
    

class BulkPaymentMethodUpload(APIView):
    
    def get(self, request, *args, **kwargs):
        payment_method_id = kwargs.get('id')
        
        if payment_method_id:
            payment_method = get_object_or_404(PaymentMethod, id=payment_method_id)
            serializer = PaymentMethodSerializer(payment_method)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        payment_methods = PaymentMethod.objects.all()
        serializer = PaymentMethodSerializer(payment_methods, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, *args, **kwargs):
        data = request.data
        
        if isinstance(data, list):
            serializer = PaymentMethodSerializer(data=data, many=True)
        else:
            return Response({'error': 'Expected a list of payment methods.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Payment methods uploaded successfully!'}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        payment_method_id = kwargs.get('id')
        payment_method = get_object_or_404(PaymentMethod, id=payment_method_id)
        serializer = PaymentMethodSerializer(payment_method, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Payment method updated successfully!'}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, *args, **kwargs):
        payment_method_id = kwargs.get('id')
        payment_method = get_object_or_404(PaymentMethod, id=payment_method_id)
        serializer = PaymentMethodSerializer(payment_method, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Payment method partially updated!'}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, *args, **kwargs):
        payment_method_id = kwargs.get('id')
        payment_method = get_object_or_404(PaymentMethod, id=payment_method_id)
        payment_method.delete()
        return Response({'message': 'Payment method deleted successfully!'}, status=status.HTTP_204_NO_CONTENT)
    
    
    
class TestimonialAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            try:
                testimonial = Testimonial.objects.get(pk=pk)
                serializer = TestimonialSerializer(testimonial)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Testimonial.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        # Return all testimonials if no ID is provided
        testimonials = Testimonial.objects.all()
        serializer = TestimonialSerializer(testimonials, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TestimonialSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            testimonial = Testimonial.objects.get(pk=pk)
        except Testimonial.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = TestimonialSerializer(testimonial, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            testimonial = Testimonial.objects.get(pk=pk)
            testimonial.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Testimonial.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        

class DepositComfirmAPIView(APIView):

    def get(self, request, deposit_id=None):
        if deposit_id:
            try:
                deposit = DepositComfirm.objects.get(id=deposit_id)
                serializer = DepositComfirmSerializer(deposit)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except DepositComfirm.DoesNotExist:
                return Response({"error": "DepositComfirm not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            deposits = DepositComfirm.objects.all()
            serializer = DepositComfirmSerializer(deposits, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = DepositComfirmSerializer(data=request.data)
        if serializer.is_valid():
            comfirmation = serializer.save()

            transaction_hash = comfirmation.transaction_hash
            wallet_credited = comfirmation.wallet_credited
            user = request.user  

            EmailNotificationManager.send_deposit_confirmation_to_company(
                user=user,
                transaction_hash=transaction_hash,
                wallet_credited=wallet_credited
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    

    def put(self, request, deposit_id=None):
        try:
            deposit = DepositComfirm.objects.get(id=deposit_id)
        except DepositComfirm.DoesNotExist:
            return Response({"error": "DepositComfirm not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = DepositComfirmSerializer(deposit, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, deposit_id=None):
        try:
            deposit = DepositComfirm.objects.get(id=deposit_id)
        except DepositComfirm.DoesNotExist:
            return Response({"error": "DepositComfirm not found"}, status=status.HTTP_404_NOT_FOUND)

        deposit.delete()
        return Response({"message": "DepositComfirm deleted successfully"}, status=status.HTTP_204_NO_CONTENT)



class UserPaymentAccountsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get all payment accounts for the authenticated user.
        """
        accounts = UserPayMentAccounts.objects.filter(user=request.user)  # Filter accounts by the authenticated user
        serializer = UserPaymentAccountsSerializer(accounts, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        Create a new payment account.
        """
        serializer = UserPaymentAccountsSerializer(data=request.data)
        if serializer.is_valid():
            # Set the user to the authenticated user before saving
            serializer.save(user=request.user)  
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update an existing payment account.
        """
        try:
            account = UserPayMentAccounts.objects.get(pk=pk, user=request.user)  # Ensure the user owns the account
        except UserPayMentAccounts.DoesNotExist:
            return Response({"detail": "Payment account not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserPaymentAccountsSerializer(account, data=request.data)
        if serializer.is_valid():
            serializer.save()  # Save the updated account
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Delete a payment account.
        """
        try:
            account = UserPayMentAccounts.objects.get(pk=pk, user=request.user)  # Ensure the user owns the account
            account.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except UserPayMentAccounts.DoesNotExist:
            return Response({"detail": "Payment account not found."}, status=status.HTTP_404_NOT_FOUND)



class BonusAPIView(APIView):
    permission_classes = [IsAuthenticated]  

    def post(self, request, *args, **kwargs):
        serializer = BonusSerializer(data=request.data)
        if serializer.is_valid():
            bonus = serializer.save()  


            user = bonus.user  
            
            EmailNotificationManager.send_bonus_email(
                recipient_email=user.email,  
                recipient_full_name=user.full_name(),  
                amount=bonus.amount
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def get(self, request, *args, **kwargs):
        if 'id' in kwargs:
            try:
                bonus = Bonus.objects.get(id=kwargs['id'])
                serializer = BonusSerializer(bonus)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Bonus.DoesNotExist:
                return Response({"detail": "Bonus not found."}, status=status.HTTP_404_NOT_FOUND)
        
        bonuses = Bonus.objects.all()
        serializer = BonusSerializer(bonuses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        try:
            bonus = Bonus.objects.get(id=kwargs['id'])
        except Bonus.DoesNotExist:
            return Response({"detail": "Bonus not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = BonusSerializer(bonus, data=request.data)
        if serializer.is_valid():
            serializer.save()  # Update the bonus
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        try:
            bonus = Bonus.objects.get(id=kwargs['id'])
            bonus.delete()  # Delete the bonus
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Bonus.DoesNotExist:
            return Response({"detail": "Bonus not found."}, status=status.HTTP_404_NOT_FOUND)
        
        
        
