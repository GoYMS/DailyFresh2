from django.urls import re_path
from django.contrib.auth.decorators import login_required

from order import views


urlpatterns = [
    # 提交订单
    re_path(r'place', login_required(views.OrderPlaceView.as_view()), name='place'),
    # 创建订单
    re_path(r'commit', login_required(views.OrderCommitView.as_view()), name='commit'),
    # 进行支付
    re_path(r'pay', login_required(views.OrderPayView.as_view()), name='pay'),
    # 查询支付结果
    re_path(r'^check$', login_required(views.OrderCheckView.as_view()), name='check'),
    # 评价
    re_path(r'^comment/(?P<order_id>\d+)$', login_required(views.CommentView.as_view()), name='comment'),
]
