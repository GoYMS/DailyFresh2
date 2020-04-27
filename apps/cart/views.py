from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import View
from django_redis import get_redis_connection

from goods.models import GoodsSKU
# Create your views here.


class CartAddView(View):
    """购物车商品增加"""
    def post(self, request):
        # 判断是否登录
        user = request.user
        if user.is_authenticated is False:
            # 用户未登录
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        # 接受数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 校验数据
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 数目是否正确
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '数目不正确'})

        # id是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)

        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 添加购物车记录
        conn = get_redis_connection('default')

        # 获取redis中的关于购物车的数据名称
        cart_key = 'cart_%d' % user.id

        # 判断是否存在
        # 如果sku_id在hash中不存在，hget返回none
        cart_count = conn.hget(cart_key, sku_id)

        if cart_count:
            count += int(cart_count)
        # 校验商品的库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        # 设置hash中sku_id对应的值
        conn.hset(cart_key, sku_id, count)
        # 获取总的商品条目数
        totla_count = conn.hlen(cart_key)

        # 返回应答
        return JsonResponse({'res': 5, 'message': '添加成功', 'totla_count': totla_count})


class CartShowView(View):
    """购物车页面"""
    def get(self, request):
        # 获取登陆的用户
        user = request.user
        # 获取用户购物车中商品的信息
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # {'商品id':商品数量}
        cart_dict = conn.hgetall(cart_key)

        skus = []
        # 保存用户购车中商品的总数目和总价格
        total_count = 0
        total_price = 0
        # 遍历获取商品的信息
        for sku_id, count in cart_dict.items():
            # 根据商品id获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 计算商品的小计
            amount = sku.price * int(count)
            # 动态给sku对象增加一个属性amount， 保存商品的小计
            sku.amount = amount
            # 动态给sku对象增加一个属性count， 保存购物车中对应商品的数量
            sku.count = count.decode('utf-8')
            # 添加
            skus.append(sku)

            total_count +=int(count)
            total_price += amount
        return render(request, 'cart.html', context={
            'total_count': total_count,
            'total_price': total_price,
            'skus': skus,
        })


class CartUpdateView(View):
    """更新购物车页面的数量"""
    def post(self, request):
        # 判断是否登录
        user = request.user
        if user.is_authenticated is False:
            # 用户未登录
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        # 接受数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 校验数据
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 数目是否正确
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '数目不正确'})

        # id是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)

        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 添加购物车记录
        conn = get_redis_connection('default')

        # 获取redis中的关于购物车的数据名称
        cart_key = 'cart_%d' % user.id

        # 校验商品的库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        # 设置hash中sku_id对应的值
        conn.hset(cart_key, sku_id, count)

        # 计算商品的总件数
        vals = conn.hvals(cart_key)  # hval获取所有的属性值

        total_count = 0
        for val in vals:

            total_count += int(val.decode())

        # 返回应答
        return JsonResponse({'res': 5, 'message': '添加成功', 'total_count':total_count})


class CartDeleteView(View):
    """删除购物车记录"""

    def post(self, request):
        # 判断是否登录
        user = request.user
        if user.is_authenticated is False:
            # 用户未登录
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        # 获取参数
        sku_id = request.POST.get('sku_id')

        # 数据校验
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '删除失败'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})
        # 找到对应的redis中的数据
        conn = get_redis_connection('default')
        cart_key = "cart_%d"%user.id
        # 删除hdel
        conn.hdel(cart_key, sku_id)

        # 计算商品的总件数
        vals = conn.hvals(cart_key)  # hval获取所有的属性值
        total_count = 0
        for val in vals:
            total_count += int(val.decode())

        return JsonResponse({'res': 3, 'total_count': total_count, 'message': '删除成功'})





