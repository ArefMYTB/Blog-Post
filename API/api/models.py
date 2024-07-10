from django.db import models
from django.contrib.auth.models import User


class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    published_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def getNumRate(self):
        rates = self.rating_set.all()
        numRate = len(rates)
        return numRate

    def getAverageRate(self):
        rates = self.rating_set.all()
        if self.getNumRate() != 0:
            avg = sum([r.rating for r in rates])/self.getNumRate()
            return avg
        else:
            return 0.0


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    blog_post = models.ForeignKey(BlogPost, on_delete=models.CASCADE)
    rating = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.blog_post.title} - {self.rating}'
