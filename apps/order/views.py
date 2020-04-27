from django.shortcuts import render, reverse, redirect
from django.views.generic import View
from django_redis import get_redis_connection
from django.http import JsonResponse
from datetime import datetime
from django.db import transaction
from django.conf import settings
from alipay import AliPay
import os

from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods
from user.models import Address


class OrderPlaceView(View):
    """提交订单页面"""
    def post(self, request):
        user = request.user
        # 获取参数sku_ids
        sku_ids = request.POST.getlist('sku_ids')

        # 校验参数
        if not sku_ids:
            # 跳转到购物车页面
            return redirect(reverse('cart:show'))

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        skus = []

        # 保存商品的总件数和总价格
        total_count = 0
        total_price = 0
        # 遍历sku_ids获取用户要购买的商品的信息
        for sku_id in sku_ids:
            # 根据商品的id获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 获取用户所要购买的商品的数量
            count = conn.hget(cart_key, sku_id)
            count = count.decode()
            # 计算商品的小计
            amount = sku.price * int(count)
            # 动态给sku增加属性count
            sku.count = count
            # 动态给sku增加属性amount
            sku.amount = amount
            skus.append(sku)
            # 累加计算商品的总件数和总价格
            total_count += int(count)
            total_price += amount

        # 运费
        transit_price = 10
        # 实际付款
        total_pay = total_price + transit_price

        # 获取用户的收件地址
        addrs = Address.objects.get(user=user)
        sku_ids = ','.join(sku_ids)
        return render(request, 'place_order.html', context={
            'addrs': addrs,
            'total_pay': total_pay,
            'transit_price': transit_price,
            'skus': skus,
            'total_count': total_count,
            'total_price': total_price,
            'sku_ids': sku_ids,
        })


class OrderCommitView(View):
    """创建订单"""
    @transaction.atomic  # mysql事物回滚
    def post(self, request):
        user = request.user

        # 接受参数
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 校验参数
        if not all([pay_method, sku_ids]):
            return JsonResponse({'res': 2, 'errmsg': '参数不完整'})

        # todo:创建订单的核心业务
        # 创建订单id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)
        # 获取地址
        addr = Address.objects.get(user=user)
        # 运费
        transit_price = 10.00
        # 总的数目和总金额
        total_count = 0
        total_price = 0

        # todo: 向df_order_info中添加一条记录
        order = OrderInfo.objects.create(order_id=order_id,
                                         user=user,
                                         addr=addr,
                                         pay_method=pay_method,
                                         total_count=total_count,
                                         total_price=total_price,
                                         transit_price=transit_price)

        # todo: 用户的订单有几个商品，需要向df_order_goods表中加入几条记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        sku_ids = sku_ids.split(',')
        for sku_id in sku_ids:
            # 获取商品的信息
            try:
                #  select_for_update()  是给这句语句加上悲观锁，防止并发
                sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
            except:
                # 商品不存在
                return JsonResponse({'res': 4, 'errmsg': '商品不存在'})
            # 从redis中获取要购买商品的数量
            count = conn.hget(cart_key, sku_id)
            count = count.decode()

            # todo:判断商品的库存
            if int(count) > sku.stock:
                return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})
            # todo:向df_order_goods表中添加一条记录
            OrderGoods.objects.create(order=order,
                                      sku=sku,
                                      count=count,
                                      price=sku.price
                                      )

            # todo:更新商品的库存和销量
            sku.stock -= int(count)
            sku.sales += int(count)
            sku.save()

            amount = sku.price * int(count)
            total_count += int(count)
            total_price += amount

        # todo:更新订单信息表中的商品的总数量和总价格
        order.total_count = total_count
        order.total_price = total_price
        order.save()

        # todo:清除用户购物车中对应的记录
        conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'res': 5, 'message': '创建成功'})


class OrderPayView(View):
    """使用支付宝进行支付"""
    def post(self, request):
        user = request.user
        # 从前端获取参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单'})
        try:
            order = OrderInfo.objects.get(user=user, order_id=order_id, pay_method=3, order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 初始化
        app_private_key_string = open("/home/yms/PycharmDemo/DjangoDemo/DailyFresh/utils/alipay/keys/private_2048.txt").read()
        alipay_public_key_string = open("/home/yms/PycharmDemo/DjangoDemo/DailyFresh/utils/alipay/keys/alipay_key_2048.txt").read()

        app_private_key_string == """
            -----BEGIN RSA PRIVATE KEY-----
            base64 encoded content
            -----END RSA PRIVATE KEY-----
        """

        alipay_public_key_string == """
            -----BEGIN PUBLIC KEY-----
            base64 encoded content
            -----END PUBLIC KEY-----
        """



        alipay = AliPay(
        appid="2016101800719127",
        app_notify_url=None,  # 默认回调url
        app_private_key_string=app_private_key_string,
        # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
        alipay_public_key_string=alipay_public_key_string,
        sign_type="RSA2",  # RSA 或者 RSA2
        debug=True  # 默认False, False是真实环境，现在使用的是沙箱环境，所以用True
        )

        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        total_pay = order.total_price + order.transit_price
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_pay),
            subject='天天生鲜%s' % order_id,
            # return_url='http://127.0.0.1:8000/user/order/1',
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})


class OrderCheckView(View):
    """查询用户的支付结果"""
    def post(self, request):
        user = request.user
        # 从前端获取参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
         return JsonResponse({'res': 1, 'errmsg': '无效的订单'})
        try:
         order = OrderInfo.objects.get(user=user, order_id=order_id, pay_method=3, order_status=1)
        except OrderInfo.DoesNotExist:
         return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 初始化
        app_private_key_string = open(
         "/home/yms/PycharmDemo/DjangoDemo/DailyFresh/utils/alipay/keys/private_2048.txt").read()
        alipay_public_key_string = open(
         "/home/yms/PycharmDemo/DjangoDemo/DailyFresh/utils/alipay/keys/alipay_key_2048.txt").read()

        app_private_key_string == """
                 -----BEGIN RSA PRIVATE KEY-----
                 base64 encoded content
                 -----END RSA PRIVATE KEY-----
             """

        alipay_public_key_string == """
                 -----BEGIN PUBLIC KEY-----
                 base64 encoded content
                 -----END PUBLIC KEY-----
             """

        alipay = AliPay(
         appid="2016101800719127",
         app_notify_url=None,  # 默认回调url
         app_private_key_string=app_private_key_string,
         # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
         alipay_public_key_string=alipay_public_key_string,
         sign_type="RSA2",  # RSA 或者 RSA2
         debug=True  # 默认False, False是真实环境，现在使用的是沙箱环境，所以用True
        )

        # 调用支付宝的交易接口查询
        while True:
            response = alipay.api_alipay_trade_query(order_id)
            # response 返回的内容
            """
            response的返回结果
            response = {
              {
                "trade_no": "2017032121001004070200176844",
                "code": "10000",
                "invoice_amount": "20.00",
                "open_id": "20880072506750308812798160715407",
                "fund_bill_list": [
                  {
                    "amount": "20.00",
                    "fund_channel": "ALIPAYACCOUNT"
                  }
                ],
                "buyer_logon_id": "csq***@sandbox.com",
                "send_pay_date": "2017-03-21 13:29:17",
                "receipt_amount": "20.00",
                "out_trade_no": "out_trade_no15",
                "buyer_pay_amount": "20.00",
                "buyer_user_id": "2088102169481075",
                "msg": "Success",
                "point_amount": "0.00",
                "trade_status": "TRADE_SUCCESS",
                "total_amount": "20.00"
              },
            }
            
            """

            code = response.get('code')

            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                # 支付成功
                trade_no = response.get('trade_no')
                # 更新订单状态
                order.trade_no = trade_no
                order.order_status = 4  # 待评价
                order.save()
                # 返回结果
                return JsonResponse({'res': 3, 'message': '支付成功'})
            elif code == '40004' or(code=='10000' and response.get('trade_status')=='WAIT_BUYER_PAY'):
                import time
                time.sleep(5)
                continue
            else:
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})


class CommentView(View):
    """订单评论"""
    def get(self, request, order_id):
        """提供评论页面"""
        user = request.user

        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))

        # 根据订单的状态获取订单的状态标题
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 获取订单商品信息
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            # 计算商品的小计
            amount = order_sku.count*order_sku.price
            # 动态给order_sku增加属性amount,保存商品小计
            order_sku.amount = amount
        # 动态给order增加属性order_skus, 保存订单商品信息
        order.order_skus = order_skus

        # 使用模板
        return render(request, "order_comment.html", {"order": order})

    def post(self, request, order_id):
        """处理评论内容"""
        user = request.user
        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))

        # 获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)

        # 循环获取订单中商品的评论内容
        for i in range(1, total_count + 1):
            # 获取评论的商品的id
            sku_id = request.POST.get("sku_%d" % i)  # sku_1 sku_2
            # 获取评论的商品的内容
            content = request.POST.get('content_%d' % i, '')  # cotent_1 content_2 content_3
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()

        order.order_status = 5  # 已完成
        order.save()

        return redirect(reverse("user:order", kwargs={"pages": 1}))








