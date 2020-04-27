from django.urls import re_path
from django.contrib.auth.decorators import login_required
from cart import views

urlpatterns = [

    # 添加购物车的数据
    re_path(r'^add$', views.CartAddView.as_view(), name='add'),
    # 显示购物车页面
    re_path(r'^$', login_required(views.CartShowView.as_view()), name='show'),
    # 更新购物车页面
    re_path(r'^update$', login_required(views.CartUpdateView.as_view()), name='update'),
    # 删除购物车
    re_path(r'^delete$', login_required(views.CartDeleteView.as_view()), name='delete'),

]
