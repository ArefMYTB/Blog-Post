from django.urls import path
from . import views


urlpatterns = [
    path("blogposts/", views.BlogPostListCreate.as_view(), name="blogpost-view-create"),
    path("blogposts/<int:pk>", views.BlogPostRetrieveUpdateDestroy.as_view(), name="update"),
    path("blogposts/list/", views.BlogPostList.as_view(), name="show")
]