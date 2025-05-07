from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import *
router = DefaultRouter()
historyRouter = DefaultRouter()
historyRouter.register(
    r'transactions', TransactionHistoryViewSet, basename='transaction-history')
historyRouter.register(
    r'revenue', RevenueViewSet, basename='revenue')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'transactions', TransactionViewSet, basename='transaction')
urlpatterns = [
    path('', include(router.urls)),
    path('history/', include(historyRouter.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth-check/', AuthCheckView.as_view(), name='auth-check'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', UpdateProfileView.as_view(), name='update-profile'),
    path('get-csrf-token/', GetCSRFToken.as_view(), name='get-csrf-token'),
    path('user/products/', UserProductsView.as_view(), name='user-products'),
]
