from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.TaskViewSet import TaskViewSet,CommentViewSet,FileUploadViewSet
from .views.TagViewSet import TagViewSet

router = DefaultRouter()
router.register(r"tasks", TaskViewSet, basename="tasks")
router.register(r"tags", TagViewSet, basename="tags")
router.register(r"comments", CommentViewSet, basename="comments")
router.register(r"file-upload", FileUploadViewSet, basename="task-files")





urlpatterns = [
    path("", include(router.urls)),
]
    