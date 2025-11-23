from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from ..models import Task, Comment, FileAttachment, Tag
from ..serializers import (
    TaskSerializer,
    CommentSerializer,
    FileAttachmentSerializer,
    TagSerializer,
    BulkTaskCreateSerializer,
)
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination



class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class TaskViewSet(viewsets.ModelViewSet):
    """
    filter/search/order
    soft delete 
    bulk-create endpoint
    """
    queryset = (
        Task.objects.filter(is_deleted=False)
        .select_related("assigned_to", "created_by")
        .prefetch_related("tags")
    )
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (FormParser, MultiPartParser)
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "priority", "assigned_to", "created_by"]
    search_fields = ["title", "description", "tags__name"]
    ordering_fields = ["due_date", "created_at", "priority"]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        # Example: allow admin to see deleted tasks via query param ?include_deleted=true
        qs = Task.objects.select_related("assigned_to", "created_by").prefetch_related("tags")
        include_deleted = self.request.query_params.get("include_deleted", "false").lower()
        if include_deleted in ("true", "1", "yes") and self.request.user.is_staff:
            return qs
        return qs.filter(is_deleted=False)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete: mark is_deleted and set deleted_at (model method handles it).
        """
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        serializer = BulkTaskCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instances = serializer.save()
        out = TaskSerializer(instances, many=True, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

   
    def partial_update(self, request, *args, **kwargs):
        # allow partial updates
        return super().partial_update(request, *args, **kwargs)


class CommentViewSet(viewsets.ModelViewSet):
    """
    Nested-like comment endpoints (we use task_pk in URL conf).
    Expected URL pattern: /tasks/{task_pk}/comments/...
    """
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        task_id = self.kwargs.get("task_pk")
        qs = Comment.objects.select_related("author").filter(is_deleted=False)
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        task_id = self.kwargs.get("task_pk")
        task = get_object_or_404(Task, pk=task_id, is_deleted=False)
        serializer.save(author=self.request.user, task=task)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FileUploadView(
    mixins.CreateModelMixin, mixins.DestroyModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """
    Handles file uploads related to a task.
    URLs expected: /tasks/{task_pk}/files/ and /tasks/{task_pk}/files/{pk}/
    """

    serializer_class = FileAttachmentSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        task_id = self.kwargs.get("task_pk")
        qs = FileAttachment.objects.all().select_related("uploaded_by")
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs.order_by("-uploaded_at")

    def perform_create(self, serializer):
        # Validate that task exists and is not deleted
        task_id = self.kwargs.get("task_pk")
        task = get_object_or_404(Task, pk=task_id, is_deleted=False)

        # File validators could be enforced in serializer.validate()
        file_obj = serializer.validated_data.get("file", None)
        if not file_obj:
            raise ValidationError({"file": "No file provided."})

        # Example: simple size check (10 MB)
        max_size = 10 * 1024 * 1024
        if file_obj.size > max_size:
            raise ValidationError({"file": "File size exceeds 10 MB limit."})

        serializer.save(uploaded_by=self.request.user, task=task, filename=file_obj.name)

    def destroy(self, request, *args, **kwargs):
        # Deleting an uploaded FileAttachment will delete the file (depends on storage)
        instance = self.get_object()
        instance.file.delete(save=False)  # remove file from storage
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


