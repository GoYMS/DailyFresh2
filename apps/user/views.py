from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.generic.base import View, reverse
from DailyFresh.settings import SECRET_KEY
# 加密
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.contrib.auth import authenticate, login, logout
import re
from django_redis import get_redis_connection
from django.core.paginator import Paginator

from user.form import RegisterForm, LoginFrom
from user.models import User
from celery_tasks.tasks import send_active_email
from user.models import Address
from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods


class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """显示注册页面"""
        register_form = RegisterForm()
        return render(request, 'register.html', context={
            'register_form': register_form
        })

    def post(self, request):
        """用户注册校验"""
        register_form = RegisterForm(request.POST)

        if register_form.is_valid():
            # 获取前端数据
            username = register_form.cleaned_data['user_name']
            pwd = register_form.cleaned_data['pwd']
            cpwd = register_form.cleaned_data['cpwd']
            email = register_form.cleaned_data['email']
            allow = request.POST.get('allow')
            # 校验参数是否完整
            if not all([username, pwd, cpwd, email]):

                return render(request,'register.html', context={
                   'errmsg': '请填写全部',
                   'register_form': register_form
                })
            # 校验用户是否存在
            try:
                use = User.objects.get(username=username)
            except Exception as e:
                use = None
            if use:
                return render(request, 'register.html', context={
                    'errmsg': '用户名已存在',
                    'register_form': register_form
                })
            # 校验密码是否正确
            if pwd != cpwd:
                return render(request, 'register.html', context={
                    'errmsg': '两次密码不一致',
                    'register_form': register_form
                })
            # 校验协议是否勾选
            if allow != 'on':
                return render(request, 'register.html', context={
                    'errmsg': '请勾选协议',
                    'register_form': register_form
                })
            # 检查邮箱不能重复
            try:
                user = User.objects.get(email=email)

            except Exception as e:
                user = None
            if user:
                return render(request, 'register.html', context={
                    'errmsg': '邮箱已经被注册',
                    'register_form': register_form
                })

            # 创建用户
            user = User.objects.create_user(username=username, password=pwd, email=email)
            # 上边的方法会自动将 is_active 改为1 也就是邮箱激活状态， 所以下边需要修改一下
            user.is_active = 0
            user.save()

            # 加密用户信息生成激活token
            serializer = Serializer(SECRET_KEY, 3600)
            info = {'confirm': user.id}
            token = serializer.dumps(info)
            # 获取到的数据是bytes类型的，需要解码
            token = token.decode()

            # 发送邮件
            send_active_email.delay(email, token, user.username)
            return redirect(reverse('user:login'))
        else:
            return render(request, 'register.html', context={
                'register_form': register_form
            })


class ActivateView(View):
    """激活邮箱"""
    def get(self, request, token):
        # 解密获取要激活的邮箱
        serializer = Serializer(SECRET_KEY,3600)
        try:

            info = serializer.loads(token)
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            # 链接过期
            return HttpResponse('激活链接已失效')


class LoginView(View):
    """登录"""
    def get(self, request, ):
        # 判断是否记住了用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', context={
            'username': username,
            'checked': checked
        })

    def post(self, request):
        form = LoginFrom(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['pwd']
            if not all([username, password]):
                return render(request, 'login.html', context={
                    'form': form,
                    'errmsg': '请填写完整'
                })
            # django自带的用户验证方法
            # django自带的验证函数
            # user = authenticate(username=username, password=password)
            # if user is not None:
            #     if user.is_active:
            #         # 用户已激活
            #         # 自带的登录方法，并且会将session存储
            #         login(request, user)
            #         response = redirect(reverse('goods:index'))
            #         # 判断是否需要记住用户名
            #         remember = request.POST.get('remember')
            #         if remember == 'on':
            #             # 记住用户名
            #             response.set_cookie('username', username, max_age=7*24*3600)
            #         else:
            #             response.delete_cookie('username')
            #
            #         return response
            #     else:
            #         return render(request, 'login.html', context={
            #             'form': form,
            #             'errmsg': '用户邮箱未激活,请先激活再登录'
            #         })
            # else:
            #     return render(request, 'login.html', context={
            #         'form': form,
            #         'errmsg': '用户名或密码错误'
            #     })

            user = User.objects.filter(username=username).first()
            if user is None:
                return render(request, 'login.html', context={'errmsg': '用户名不存在'})

            if user.check_password(password) is None:
                return render(request, 'login.html', context={'errmsg': '用户名或密码错误'})
            if user.is_active == 0:
                return render(request, 'login.html', context={'errmsg': '用户邮箱未激活,请先激活在登录'})

            # 自带的登录方法，并且会将session存储
            login(request, user)
            # 获取登录成功后要跳转的路径，因为使用的是自带的验证是否登陆的装饰器，如果没有登录会跳转到设置的登录页面
            # url后边会带上跳转前的路径，所以读取后边的路径，登陆后还跳转到之前的页面
            # 需要注意的后，前端form表单中的action不要写，  action不写会跳转到地址栏中的路径
            next_url = request.GET.get('next', reverse('goods:index'))

            response = redirect(next_url)
            # 判断是否需要记住用户名
            remember = request.POST.get('remember')
            if remember == 'on':
                # 记住用户名
                response.set_cookie('username', username, max_age=7 * 24 * 3600)
            else:
                response.delete_cookie('username')

            return response

        else:
            return render(request, 'login.html', context={'form': form})


class LogoutView(View):
    """退出"""

    def get(self, request):
        logout(request)
        return redirect(reverse('goods:index'))


class UserInfoView(View):
    """用户个人信息"""
    def get(self, request):
        user = request.user
        try:
            address = Address.objects.get(user=user)
        except Address.DoesNotExist:
            address = None

        # 获取用户的历史浏览记录, 从redis中获取
        # 创建对象
        con = get_redis_connection('default')
        # 在redis中存储的是list形式的
        history_key = 'history_%d' % user.id
        # 获取用户最新浏览的5个商品的id
        # Redis Lrange 返回列表中指定区间内的元素，区间以偏移量 START 和 END 指定。
        # 其中 0 表示列表的第一个元素， 1 表示列表的第二个元素
        sku_ids = con.lrange(history_key, 0, 4)
        # 从数据库中查询用户浏览的商品的具体信息
        goods = GoodsSKU.objects.filter(id__in=sku_ids)
        # 由于数据库中查出来的顺序不是按照浏览记录的顺序，所以排序，按照顺序取出
        goods_li = []
        for sku_id in sku_ids:
            goods = GoodsSKU.objects.get(id=sku_id)
            goods_li.append(goods)

        page = 'user'
        return render(request, 'user_center_info.html', context={
            'address': address,
            'goods_li': goods_li,
            'page': page

        })


class UserOrderView(View):
    """购物车信息"""
    def get(self, request, pages):
        # 获取登陆的用户
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        # 遍历获取订单商品的信息
        for order in orders:
            # 根据order查找对应的订单商品信息
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            # 遍历商品订
            for order_sku in order_skus:
                # 计算小计
                amount = order_sku.count * order_sku.price
                # 动态增加商品的小计
                order_sku.amount = amount
            # 动态给商品增加属性
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders, 1)
        # 判断获取的page的数据准确性
        # 获取传过来的页数
        try:
            pages = int(pages)
        except Exception as e:
            # 如果传过来的page数据不对，就自动为第一页
            pages = 1
        # 如果传过来的页数超过本应的页数
        if pages > paginator.num_pages:  # num_pages:获取总共有多少页
            pages = 1

        # 获取第page页的实例对象
        order_page = paginator.page(pages)  # page(页数):获取这页的数据

        return render(request, 'user_center_order.html', context={
            'page': 'order',
            'order_page': order_page,
            'pages': pages

        })


class UserSiteView(View):
    """用户地址信息"""
    def get(self, request):
        user = request.user
        try:
            address = Address.objects.get(user=user)
        except Address.DoesNotExist:
            address = None
        page = 'site'
        return render(request, 'user_center_site.html', context={
            'address': address,
            'page': page
        })

    def post(self, request):
        # 获取用户传入的地址信息
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        page = 'site'
        # 校验用户的信息的格式是否正确
        if not all([receiver, addr, zip_code, phone]):
            return render(request, 'user_center_site.html', context={
                'errmsg': '请填写全部内容',
                'page': page
            })
        # 校验手机号
        if not re.match(r'^1[34578][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', context={
                'errmsg': '手机格式不正确',
                'page': page
            })
        # 获取当前用户
        user = request.user
        # 存储用户的地址信息
        Address.objects.create(user=user, addr=addr, receiver=receiver, zip_code=zip_code, phone=phone)

        return redirect(reverse('user:site'))







