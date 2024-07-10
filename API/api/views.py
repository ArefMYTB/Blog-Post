from django.shortcuts import render, redirect
from rest_framework import generics
from .models import BlogPost, Rating
from .serializers import BlogPostSerializers
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
import numpy as np
from sklearn.cluster import DBSCAN

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
            detect_and_delete_fake_ratings(blog_post)
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

            if created:
                # Check if user has rated any blog recently
                recent_ratings = Rating.objects.filter(user=request.user,
                                                       created_at__gte=timezone.now() - timedelta(hours=1))
                if recent_ratings.exists():
                    return JsonResponse({'error': 'You can only rate once per hour.'})

            if created or user_rating.rating != rating:
                user_rating.rating = rating
                user_rating.save()
            else:
                user_rating.delete()

        return redirect('show')


def extract_features(ratings):
    now = timezone.now()
    features = np.array([
        [(now - rating.created_at).total_seconds(), rating.rating]
        for rating in ratings
    ])
    return features


def detect_and_delete_fake_ratings(blog_post, eps=3600, min_samples=10):
    """
    Detect clusters of ratings submitted within 'eps' seconds with the same rating value.
    - eps: Maximum distance between two samples for them to be considered as in the same neighborhood (in seconds).
    - min_samples: The number of samples in a neighborhood for a point to be considered as a core point.
    """
    ratings = Rating.objects.filter(blog_post=blog_post.id)
    if len(ratings) < min_samples:
        return False

    # print(f"{blog_post.title}: {ratings}")

    features = extract_features(ratings)
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean').fit(features)
    labels = clustering.labels_

    # If a cluster is detected (more than 10 ratings with the same label), delete those ratings
    for label in set(labels):
        if label != -1 and list(labels).count(label) >= min_samples:
            clustered_ratings = [ratings[i] for i in range(len(ratings)) if labels[i] == label]
            Rating.objects.filter(id__in=[r.id for r in clustered_ratings]).delete()
            return True

    return False
