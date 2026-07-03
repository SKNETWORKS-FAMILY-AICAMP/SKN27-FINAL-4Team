import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from myprofile.views import profile_detail

User = get_user_model()
user = User.objects.get(id=3)

factory = RequestFactory()
request = factory.get('/api/myprofile/profile/')
request.user = user

response = profile_detail(request)

print(f"Status Code: {response.status_code}")
print(f"Response Content: {response.data}")
