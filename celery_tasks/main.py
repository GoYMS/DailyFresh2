from celery import Celery
from django.conf import settings

# 
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DailyFresh.settings")
django.setup()

# 创建一个Celery类的实例对象
#               起一个名字          指定使用什么当做中间人
app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/2')

# app.autodiscover_tasks(settings.INSTALLED_APPS)

