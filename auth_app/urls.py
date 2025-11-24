from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (RegisterView, CurrentUserView , AllUsersView, task_overview, user_performance, task_trends, export_tasks)


urlpatterns = [
    # Signup
    path("register/", RegisterView.as_view(), name="register"),

    # Login -> returns access + refresh tokens
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),

    # Refresh token
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Current user profile
    path("user-profile/", CurrentUserView.as_view(), name="current_user"),
    path("all-users/", AllUsersView.as_view({'get': 'list'}), name="all_users"),
    
    # Analytics endpoints
    path('analytics/overview/', task_overview, name='task_overview'),
    path('analytics/user-performance/', user_performance),
    path('analytics/trends/', task_trends),
    path('analytics/export/', export_tasks),
]




