from django.urls import re_path
from goods import views

urlpatterns = [
    # 商品首页
    re_path(r'^index/$', views.IndexView.as_view(), name='index'),
    # 商品详情页
    re_path(r'^goods/(?P<goods_id>\d*)$', views.DetailView.as_view(), name='detail'),
    # 商品列表页
    re_path(r'^list/(?P<type_id>\d*)/(?P<page>\d*)$', views.ListView.as_view(), name='list'),

]
