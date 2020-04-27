from django.contrib.auth.decorators import login_required
from django.urls import re_path
from user import views

urlpatterns = [
    # 注册页面
    re_path(r'^register/$', views.RegisterView.as_view(), name='register'),
    # 激活邮箱
    re_path(r'^active/(?P<token>.*)$', views.ActivateView.as_view(), name='active'),
    # 登录
    re_path(r'^login/$', views.LoginView.as_view(), name='login'),
    # 退出
    re_path(r'^logout/$', views.LogoutView.as_view(), name='logout'),
    # 用户中心
    re_path(r'^info/$', login_required(views.UserInfoView.as_view()), name='info'),
    # 订单
    re_path(r'^order/(?P<pages>\d+)$', login_required(views.UserOrderView.as_view()), name='order'),
    # 收货地址
    re_path(r'^site/$', login_required(views.UserSiteView.as_view()), name='site'),
]
