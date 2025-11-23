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
from django.contrib.auth.models import User





class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class TaskViewSet(viewsets.ModelViewSet):
    """
    filter/search/order
    soft delete 
    bulk-create endpoint
    """
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "priority", "assigned_to", "created_by"]
    search_fields = ["title", "description", "tags__name"]
    ordering_fields = ["due_date", "created_at", "priority"]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        # Base queryset with related fields
        qs = Task.objects.select_related("assigned_to", "created_by").prefetch_related("tags")
        # Filter deleted tasks unless admin explicitly requests
        include_deleted = self.request.query_params.get("include_deleted", "false").lower()
        if include_deleted  in ("true", "1", "yes") :
            print("i am working")
            qs = qs.filter(is_deleted=True)

        # Filter by current user
        return qs.filter(created_by=self.request.user)

   
   

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
    
    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        print("perform_update called")
        serializer.save()

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data

        # Update normal fields
        for field in ['title', 'description', 'status', 'priority', 'due_date', 'assigned_to']:
            if field in data:
                if field == 'assigned_to' and data[field] is not None:
                    try:
                        user = User.objects.get(pk=data[field])
                        setattr(instance, field, user)
                    except User.DoesNotExist:
                        return Response({"assigned_to": "User not found"}, status=status.HTTP_400_BAD_REQUEST)
                elif field == 'due_date' and data[field]:
                    setattr(instance, field, data[field])
                else:
                    setattr(instance, field, data[field])
        instance.save()

        # Handle tags manually
        tags_data = data.get('tags')
        if tags_data is not None:
            for tag in tags_data:
                # If tag is string
                tag_name = tag.get('name') if isinstance(tag, dict) else str(tag)
                if tag_name:
                    tag_obj, _ = Tag.objects.get_or_create(name=tag_name)
                    instance.tags.add(tag_obj)  # add() will avoid duplicates

        # Prepare response manually
        response_data = {
            "id": instance.id,
            "title": instance.title,
            "description": instance.description,
            "status": instance.status,
            "priority": instance.priority,
            "due_date": instance.due_date,
            "assigned_to": instance.assigned_to.id if instance.assigned_to else None,
            "created_by": instance.created_by.username,
            "tags": [{"id": t.id, "name": t.name} for t in instance.tags.all()],
        }
        return Response(response_data, status=status.HTTP_200_OK)
    
    
    def create(self, request, *args, **kwargs):
        data = request.data
        user = request.user

        # Extract tags from payload
        tags_data = data.pop('tags', [])

        # Create task
        task = Task.objects.create(
            title=data.get('title'),
            description=data.get('description'),
            status=data.get('status', 'todo'),
            priority=data.get('priority', 'medium'),
            due_date=data.get('due_date'),
            assigned_to=User.objects.get(pk=data['assigned_to']) if data.get('assigned_to') else None,
            created_by=user
        )

        # Handle tags: create if not exists, then add to task
        for tag in tags_data:
            tag_name = tag.get('name') if isinstance(tag, dict) else str(tag)
            if tag_name:
                tag_obj, _ = Tag.objects.get_or_create(name=tag_name)
                task.tags.add(tag_obj)

        serializer = self.get_serializer(task)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
  


# comment view set 
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




# file upload view
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


