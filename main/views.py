
from rest_framework import viewsets
from django.db.models.functions import TruncMonth
from django.db.models import Sum, F, FloatField
from .models import TransactionItem
from rest_framework import generics, permissions, parsers, viewsets
# your serializers
from .serializers import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CustomUser, Product  # your custom user model
from django.contrib.auth import authenticate, login, logout
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.db import transaction as db_tx
from rest_framework.decorators import action


@method_decorator(ensure_csrf_cookie, name='dispatch')
class GetCSRFToken(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"detail": "CSRF cookie set"})


class RegisterView(generics.CreateAPIView):
    """
    API endpoint that allows new users to register.
    Accepts multipart/form-data (to handle avatar image) and returns the created user.
    """
    serializer_class = RegisterSerializer                              # uses our ModelSerializer to create users :contentReference[oaicite:3]{index=3}
    # open to anonymous users :contentReference[oaicite:4]{index=4}
    permission_classes = [permissions.AllowAny]
    # handle file uploads & form data :contentReference[oaicite:5]{index=5}
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        user = authenticate(request,
                            username=request.data.get('email'),
                            password=request.data.get('password'))
        if user:
            # creates session :contentReference[oaicite:3]{index=3}
            login(request, user)
            return Response({'detail': 'Login successful'}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'detail': 'Logged out'}, status=status.HTTP_200_OK)


class AuthCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({'isAuthenticated': request.user.is_authenticated})


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'avatarUrl': request.build_absolute_uri(user.avatar.url) if user.avatar else None,
        })


class UpdateProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        # only this user’s products
        return Product.objects.filter(user=self.request.user).order_by('-created')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        q = request.query_params.get('q', '')
        qs = self.get_queryset().filter(name__icontains=q)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class UserProductsView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        email = self.request.query_params.get('email')
        return Product.objects.filter(user__email=email)


class TransactionViewSet(viewsets.ViewSet):
    @db_tx.atomic
    def create(self, request):
        items = request.data.get('items', [])
        if not items:
            return Response({'error': 'No items provided.'}, status=status.HTTP_400_BAD_REQUEST)

        txn = Transaction.objects.create()
        for it in items:
            prod = Product.objects.get(id=it['product_id'])
            if prod.quantity < it['quantity']:
                db_tx.set_rollback(True)
                return Response({'error': f'Insufficient stock for {prod.name}.'}, status=status.HTTP_400_BAD_REQUEST)
            prod.quantity -= it['quantity']
            prod.save()
            TransactionItem.objects.create(
                transaction=txn,
                product=prod,
                quantity=it['quantity'],
                price_at_transaction=prod.price
            )
        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


class TransactionHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List all transactions that include products owned by the current user.
    """
    serializer_class = TransactionHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # filter transactions via the through model:
        # only those transactions having at least one item whose product.user == request.user
        return Transaction.objects.filter(
            transactionitem__product__user=self.request.user
        ).distinct().order_by('-created_at')
# main/views.py


class RevenueViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """
        GET /api/revenue/ → [
            { month: "2025-01", revenue: 1234.56 },
            { month: "2025-02", revenue: 2345.67 },
            …
        ]
        """
        qs = (
            TransactionItem.objects
            # only this user’s products
            .filter(product__user=request.user)
            .annotate(month=TruncMonth('transaction__created_at'))
            .values('month')
            .annotate(
                revenue=Sum(
                    F('quantity') * F('price_at_transaction'),
                    output_field=FloatField()
                )
            )
            .order_by('month')
        )
        # Format month as "YYYY-MM" strings
        data = [
            {'month': entry['month'].strftime(
                '%Y-%m'), 'revenue': entry['revenue']}
            for entry in qs
        ]
        return Response(data)
