from django.db import models
from django.conf import settings
from django.utils import timezone


User = settings.AUTH_USER_MODEL


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)


    def __str__(self):
        return self.name
class Task(models.Model):
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('archived', 'Archived'),
    ]
    PRIORITY_CHOICES = [
        ('low','Low'), ('medium','Medium'), ('high','High'), ('critical','Critical')
    ]

    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo', db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', db_index=True)
    created_by = models.ForeignKey(User, related_name='created_tasks', on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(User, related_name='assigned_tasks', null=True, blank=True, on_delete=models.SET_NULL)
    tags = models.ManyToManyField(Tag, blank=True)
    due_date = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)


    class Meta:
        indexes = [
        models.Index(fields=['status','priority']),
        ]


    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()


    def __str__(self):
        return self.title


class Comment(models.Model):
    task = models.ForeignKey(Task, related_name='comments', on_delete=models.CASCADE)
    author = models.ForeignKey(User, related_name='comments', on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)


    def soft_delete(self):
        self.is_deleted = True
        self.save()


class FileAttachment(models.Model):
    task = models.ForeignKey(Task, related_name='files', on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(User, related_name='uploads', on_delete=models.CASCADE)
    file = models.FileField(upload_to='task_files/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveIntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = self.file.name
        if self.file and not self.size:
            try:
                self.size = self.file.size
            except Exception:
                pass
        super().save(*args, **kwargs)