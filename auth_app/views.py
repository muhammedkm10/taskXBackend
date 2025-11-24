from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from .serializers import RegisterSerializer, UserSerializer
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Count
from django.db.models.functions import TruncDate
from task_app.models import Task
from django.db.models import Q


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
    
    
class AllUsersView(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    # Disable pagination
    pagination_class = None
    
    


#  TASK OVERVIEW (STATUS + PRIORITY COUNTS)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def task_overview(request):
    user = request.user
    print("user",user)

    # Only user's tasks (created by or assigned to)
    base_qs = Task.objects.filter(
        Q(created_by=user) | Q(created_by=user)
    )

    # Group by status
    status_counts = base_qs.values("status").annotate(total=Count("id"))

    # Group by priority
    priority_counts = base_qs.values("priority").annotate(total=Count("id"))

    return Response({
        "status_counts": status_counts,
        "priority_counts": priority_counts
    })


#  USER PERFORMANCE (HOW MANY TASKS YOU COMPLETED)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_performance(request):
    user = request.user

    data = Task.objects.filter(
        created_by=user,
        status="done"
    ).values("assigned_to__username").annotate(total=Count("id"))

    return Response(data)


#  TRENDS (TASKS CREATED PER DAY)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def task_trends(request):
    user = request.user

    daily = Task.objects.filter(
        Q(created_by=user) | Q(assigned_to=user)
    ).annotate(
        day=TruncDate("created_at")
    ).values("day").annotate(total=Count("id")).order_by("day")

    return Response(daily)


#  EXPORT TASKS (ONLY USER TASKS)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_tasks(request):
    user = request.user

    tasks = Task.objects.filter(
        Q(created_by=user) | Q(assigned_to=user)
    ).values()

    return Response(list(tasks))
