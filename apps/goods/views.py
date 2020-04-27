from django.shortcuts import render, redirect
from django.views.generic.base import reverse
from django.views.generic.base import View
from django_redis import get_redis_connection
from django.core.cache import cache
from django.core.paginator import Paginator
# Create your views here.

from goods.models import GoodsType, IndexPromotionBanner, IndexTypeGoodsBanner, IndexGoodsBanner
from goods.models import GoodsSKU
from order.models import OrderGoods


class IndexView(View):

    def get(self, request):
        """首页"""

        # 判断缓存中是否有数据
        context = cache.get('index_page_data')

        if context is None:
            # 获取商品的种类信息
            types = GoodsType.objects.all()

            # 获取首页轮播商品信息
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')

            # 获取首页促销活动信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            # 获取首页分类商品展示信息
            for type in types:
                # 获取type种类首页分类商品的图片展示信息
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
                # 获取type种类首页分类商品的文字展示信息
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

                # 动态给type增加属性
                type.image_banners = image_banners
                type.title_banners = title_banners
            context = {
                'types': types,
                'goods_banners': goods_banners,
                'promotion_banners': promotion_banners,

            }
            # 将从数据库中获取到的数据放入到缓存中
            cache.set('index_page_data', context, 3600)

        # 获取用户购物车中商品的数量
        # 使用redis中的hash存储方式存储购物车的记录
        # 判断是否登录
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 如果登录，获取数量
            conn = get_redis_connection('default')
            # 获取hash键值
            cart_key = 'cart_%d' % user.id
            # 通过hlen方法获取数量
            cart_count = conn.hlen(cart_key)

        # 更新context
        context.update(cart_count=cart_count)
            
        return render(request, 'index.html', context)


class DetailView(View):
    """商品详情页"""
    def get(self, request, goods_id):
        """显示商品详情页"""
        # 判断传过来的商品有没有
        try:
            good = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))
        # 获取新品推荐

        new_goods = GoodsSKU.objects.filter(type=good.type).order_by('-create_time')[0:2:1]

        # 获取商品的品论信息
        good_orders = OrderGoods.objects.filter(sku=good).exclude(comment='')

        # 获取商品的分类信息
        types = GoodsType.objects.all()

        # 购物车的信息
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 如果登录，获取数量
            conn = get_redis_connection('default')
            # 获取hash键值
            cart_key = 'cart_%d' % user.id
            # 通过hlen方法获取数量
            cart_count = conn.hlen(cart_key)

            # 添加用户的浏览记录
            conn = get_redis_connection('default')
            history_key = 'history_%d' % user.id
            # 移除表中与之相同的
            conn.lrem(history_key, 0, goods_id)
            # 把goods_id 插入到列表左侧
            conn.lpush(history_key, goods_id)
            # 只保存最新的五个历史记录
            conn.ltrim(history_key, 0, 4)

        return render(request, 'detail.html', context={
            'good': good,
            'new_goods': new_goods,
            'cart_count': cart_count,
            'good_orders': good_orders,
            'types': types
        })


# 种类id，页码，排序方式
# /种类id / 页码 ? sort=排序方式
class ListView(View):
    """列表页"""
    def get(self, request, type_id, page):
        types = GoodsType.objects.all()
        # 获取种类信息
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            # 种类不存在
            return redirect(reverse('goods:index'))
        # 获取排序的方式
        # 默认： ‘default’  价格：’price‘  销量：’hot‘

        sort = request.GET.get('sort')

        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('id')

        # 对数据进行分页
        paginator = Paginator(skus, 2)  # 第一个参数：数据列表  第二个参数：每页显示几个

        # 获取传过来的页数
        try:
            page = int(page)
        except Exception as e:
            # 如果传过来的page数据不对，就自动为第一页
            page = 1
        # 如果传过来的页数超过本应的页数
        if page > paginator.num_pages:  # num_pages:获取总共有多少页
            page = 1
        # 获取第page页的实例对象
        sku_page = paginator.page(page)  # page(页数):获取这页的数据

        # todo：进行页码的控制，也马上最多显示5个页码
        # 获取购物车中的商品数量
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 如果登录，获取数量
            conn = get_redis_connection('default')
            # 获取hash键值
            cart_key = 'cart_%d' % user.id
            # 通过hlen方法获取数量
            cart_count = conn.hlen(cart_key)
        # 获取新品推荐

        new_goods = GoodsSKU.objects.filter(type=type).order_by('-create_time')[0:2:1]
        return render(request, 'list.html', context={
            "cart_count": cart_count,
            'sku_page': sku_page,
            'sort': sort,
            'type': type,
            'new_goods': new_goods,
            'types': types

        })




