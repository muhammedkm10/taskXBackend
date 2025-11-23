from rest_framework import serializers
from .models import Task, Comment, FileAttachment, Tag
from django.contrib.auth import get_user_model


User = get_user_model()

# tag serializer
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id','name']

#file attachment serializer  
class FileAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.ReadOnlyField(source='uploaded_by.id')
    file_url = serializers.SerializerMethodField()


    class Meta:
        model = FileAttachment
        fields = ['id','filename','file','file_url','content_type','size','uploaded_at','uploaded_by']
        read_only_fields = ['id','file_url','uploaded_at','uploaded_by']


    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

# task serializer
class TaskSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.username')
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)
    tags = TagSerializer(many=True, required=False)
    files = FileAttachmentSerializer(many=True, read_only=True)


    class Meta:
        model = Task
        fields = ['id','title','description','status','priority','due_date','tags','assigned_to','created_by','created_at','updated_at','files']


    def create(self, validated_data):
        tags_data = validated_data.pop('tags', [])
        user = self.context['request'].user
        task = Task.objects.create(created_by=user, **validated_data)

        for tag in tags_data:
            # Ensure we get the string value from tag object
            tag_name = tag.get('name') if isinstance(tag, dict) else str(tag)
            if tag_name:
                print("tag_name",tag_name)
                tag_obj, created = Tag.objects.get_or_create(name=tag_name)
                task.tags.add(tag_obj)

        return task


  
    
    



# comment serializer
class CommentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.id')
    class Meta:
        model = Comment
        fields = ['id','task','author','content','created_at','updated_at']
        read_only_fields = ['id','author','created_at','updated_at']


    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)
    
    
    
# bulk task create serializer
class BulkTaskCreateSerializer(serializers.ListSerializer):
    child = TaskSerializer()


    def create(self, validated_data):
        user = self.context['request'].user
        instances = []
        for item in validated_data:
            tags = item.pop('tags', [])
            t = Task.objects.create(created_by=user, **item)
            for tag in tags:
                tag_obj, _ = Tag.objects.get_or_create(name=tag.get('name'))
                t.tags.add(tag_obj)
            instances.append(t)
            return instances