from django.shortcuts import render, redirect
from rest_framework import generics
from .models import BlogPost, Rating
from .serializers import BlogPostSerializers
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

class BlogPostListCreate(generics.ListCreateAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializers


class BlogPostRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializers
    lookup_field = "pk"


class BlogPostList(APIView):
    def get(self, request, format=None):
        title = request.query_params.get("title", "")

        if title:
            blog_posts = BlogPost.objects.filter(title_icontains=title)
        else:
            blog_posts = BlogPost.objects.all()

        user_ratings = {}
        if request.user.is_authenticated:
            ratings = Rating.objects.filter(user=request.user)
            user_ratings = {rating.blog_post.id: rating.rating for rating in ratings}

        # serializer = BlogPostSerializers(blog_posts, many=True)
        # context = {"data": serializer.data, "user_ratings": user_ratings}

        data = []
        for blog_post in blog_posts:
            data.append({
                'id': blog_post.id,
                'title': blog_post.title,
                'rate': blog_post.getAverageRate(),
                'numRate': blog_post.getNumRate(),
                'user_rating': int(user_ratings.get(blog_post.id, 0))
            })
        context = {"data": data}

        return render(request, "api/blogPostList.html", context=context)

    @csrf_exempt
    def post(self, request):

        title_id = request.POST.get('title_id')
        rating = request.POST.get('rating')
        if title_id and rating:
            blog_post = BlogPost.objects.get(id=title_id)
            rating = int(rating)

            user_rating, created = Rating.objects.get_or_create(user=request.user, blog_post=blog_post,
                                                                defaults={'rating': rating})

            if created or user_rating.rating != rating:
                user_rating.rating = rating
                user_rating.save()
            else:
                user_rating.delete()

        return redirect('show')
