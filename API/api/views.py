from django.shortcuts import render, redirect
from rest_framework import generics
from .models import BlogPost, Rating
from .serializers import BlogPostSerializers
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
import numpy as np
from sklearn.cluster import DBSCAN


def loginPage(request):

    page = 'login'

    if request.user.is_authenticated:
        return redirect('show')

    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(username=username)

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('show')
            else:
                return JsonResponse({'error': 'Username or Password is wrong!'})

        except:
            return JsonResponse({'error': 'User does not exist :('})

    context = {'page': page}
    return render(request, "api/login_register.html", context)


def logoutUser(request):
    logout(request)
    return redirect('login')


def registerPage(request):

    page = 'register'
    form = UserCreationForm()

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request, user)
            return redirect('show')
        else:
            return JsonResponse({'error': 'Some problem with form.'})

    context = {'page': page, 'form': form}
    return render(request, "api/login_register.html", context)


class BlogPostListCreate(generics.ListCreateAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializers


class BlogPostRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializers
    lookup_field = "pk"


class BlogPostList(APIView):
    def get(self, request, format=None):
        # title = request.query_params.get("title", "")
        title = request.GET.get('q') if request.GET.get('q') != None else ''

        if title:
            blog_posts = BlogPost.objects.filter(title__icontains=title)
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
            numRate = blog_post.getNumRate()
            detect_and_delete_fake_ratings(blog_post)
            data.append({
                'id': blog_post.id,
                'title': blog_post.title,
                'rate': blog_post.getAverageRate(),
                'numRate': numRate if numRate < 1000 else "1k+",
                'user_rating': int(user_ratings.get(blog_post.id, -1))
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

            # if created:
            #     # Check if user has rated any blog recently
            #     recent_ratings = Rating.objects.filter(user=request.user,
            #                                            created_at__gte=timezone.now() - timedelta(hours=1))
            #     if recent_ratings.exists():
            #         return JsonResponse({'error': 'You can only rate once per hour.'})

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


def detect_and_delete_fake_ratings(blog_post, eps=3600, min_samples=200):
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

    # print(features)
    # print(clustering)
    # print(labels)

    # If a cluster is detected (more than 200 rating with the same label and rating value), delete those ratings
    clusters = {}
    for i, label in enumerate(labels):
        if label != -1:
            clusters[label] = clusters.get(label, []) + [ratings[i]]

    for cluster_ratings in clusters.values():
        if len(cluster_ratings) >= min_samples:
            rating_values = [rating.rating for rating in cluster_ratings]
            most_common_rating = max(set(rating_values), key=rating_values.count)
            count_most_common = rating_values.count(most_common_rating)

            # If a significant portion of the ratings in the cluster are the same, delete those ratings
            if count_most_common >= min_samples:
                ratings_to_delete = [r for r in cluster_ratings if r.rating == most_common_rating]
                Rating.objects.filter(id__in=[r.id for r in ratings_to_delete]).delete()
                print("Anomaly Rates Deleted")
                return True

    return False
