from rest_framework import serializers
from .models import BlogPost

class BlogPostSerializers(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = ["id", "title"]
