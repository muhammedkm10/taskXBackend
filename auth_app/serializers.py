from rest_framework import serializers
from django.contrib.auth.models import User
from task_app.serializers import TaskSerializer 
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "password2"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    assigned_tasks = TaskSerializer(many=True, read_only=True)
    class Meta:
        model = User
        fields = ["id", "username", "email","last_login","date_joined","assigned_tasks"]


