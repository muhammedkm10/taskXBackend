from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.TaskViewSet import TaskViewSet
from .views.TagViewSet import TagViewSet

router = DefaultRouter()
router.register(r"tasks", TaskViewSet, basename="tasks")
router.register(r"tags", TagViewSet, basename="tags")

urlpatterns = [
    path("", include(router.urls)),
]
    