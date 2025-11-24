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
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "priority", "assigned_to", "created_by"]
    search_fields = ["title", "description", "tags__name"]
    ordering_fields = ["due_date", "created_at", "priority"]
    pagination_class = StandardResultsSetPagination
    
    
    # getting data to front end 
    def get_queryset(self):
        # Base queryset with related fields
        qs = Task.objects.select_related("assigned_to", "created_by").prefetch_related("tags")
        print(qs)
        # Filter deleted tasks unless admin explicitly requests
        include_deleted = self.request.query_params.get("include_deleted", "false").lower()
        if include_deleted  in ("true", "1", "yes") :
            qs = qs.filter(is_deleted=True)
        # Filter by current user
        return qs.filter(created_by=self.request.user)


    
    # assign task to user
    @action(detail=True, methods=['post'], url_path='assign-user/(?P<user_id>[^/.]+)')
    def assign_user(self, request, pk=None, user_id=None):
        task = self.get_object()
        print("user id",user_id,pk)
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"success": False, "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if task.assigned_to:
            if task.assigned_to.id == user.id:
                return Response({
                    "success": False,
                    "message": f"User '{user.username}' is already assigned to this task."
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Optional: notify that the previous user will be replaced
                old_user = task.assigned_to
                task.assigned_to = user
                task.save()
                return Response({
                    "success": True,
                    "message": f"Task reassigned from '{old_user.username}' to '{user.username}'.",
                    "data": {
                        "task_id": task.id,
                        "assigned_to": {"id": user.id, "username": user.username, "full_name": user.get_full_name()}
                    }
                }, status=status.HTTP_200_OK)

        # No user assigned yet, assign directly
        task.assigned_to = user
        task.save()
        return Response({
            "success": True,
            "message": f"User '{user.username}' assigned to task '{task.title}'",
            "data": {
                "task_id": task.id,
                "assigned_to": {"id": user.id, "username": user.username, "full_name": user.get_full_name()}
            }
        }, status=status.HTTP_200_OK)


    # soft delete implementation
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # bulk create endpoint
    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        serializer = BulkTaskCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instances = serializer.save()
        out = TaskSerializer(instances, many=True, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)
    
    # perform create and update
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
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    
    def get_queryset(self):
        qs = Comment.objects.select_related("author").filter(is_deleted=False)

        # Only check task_pk for list() API call
        if self.action == "list":
            task_id = self.request.query_params.get("task_pk")
            print("task id in comment", task_id)
            if not task_id:
                raise ValidationError({"task_pk": "task_pk is required"})
            qs = qs.filter(task_id=task_id)

        return qs.order_by("-created_at")

    def create(self, request, *args, **kwargs):
        task_id = self.request.data.get("task_id")  # <-- from request body
        if not task_id:
            raise ValidationError({"task_id": "task_id is required"})
        task = get_object_or_404(Task, pk=task_id, is_deleted=False)
        print("task",task.title)
        comment = Comment.objects.create(
            task=task,
            author=request.user,
            content=request.data.get("content", ""),
        )
        print("comment",comment.content,comment.author)
        serializer = self.get_serializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user:
            return Response({"detail": "You do not have permission to delete this comment."}, status=status.HTTP_403_FORBIDDEN)
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def partial_update(self, request, *args, **kwargs):
        print("partial update called",request.data) 
        return super().partial_update(request, *args, **kwargs)




# file upload view
class FileUploadViewSet(viewsets.ModelViewSet):
    serializer_class = FileAttachmentSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    pagination_class = None

    # fetching files
    def get_queryset(self):
        task_id = self.request.query_params.get("task_pk")
        qs = FileAttachment.objects.select_related("uploaded_by")
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs.order_by("-uploaded_at")


    # updload files
    def perform_create(self, serializer):
        task_id = self.request.data.get("task_id")
        if not task_id:
            raise ValidationError({"task_id": "task_id is required"})
        task = get_object_or_404(Task, pk=task_id, is_deleted=False)
        file_obj = serializer.validated_data.get("file")
        if not file_obj:
            raise ValidationError({"file": "No file provided."})
        serializer.save(
            uploaded_by=self.request.user,
            task=task,
            filename=file_obj.name,
            content_type=file_obj.content_type,
            size=file_obj.size,
        )


    # destroy files
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.file.delete(save=False)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


