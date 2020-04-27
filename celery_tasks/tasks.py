from celery_tasks.main import app
from goods.models import GoodsType, IndexPromotionBanner, IndexTypeGoodsBanner,IndexGoodsBanner
from django.template import loader
import os
from django.conf import settings


# 发出任务的放在了admin中，以便于后台更改了数据后能够及时修正数据
@app.task
def send_static_index():
    """首页"""
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
        'promotion_banners': promotion_banners
    }
    # 1. 加载模板文件，返回模板对象
    temp = loader.get_template('static_index.html')
    # 2. 模板渲染,生成一个html文件的内容
    static_index_html = temp.render(context)
    # 3. 生成首页对应的静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')

    with open(save_path, 'w') as f:
        f.write(static_index_html)


@app.task
def send_active_email(email, token, username):
    """发送邮件方法"""
    from django.core.mail import EmailMultiAlternatives
    # subject 邮件主题，  from_email 从哪个邮箱发出  to ：发送给谁，注意是一个列表形式的
    subject, from_email, to = '来自天天生鲜的激活邮件', settings.EMAIL_HOST_USER, email

    text_content = '欢迎注册天天生鲜网站'
    html_content = '''
                            <p>感谢{}注册<a href="http://{}/user/active/{}">点击激活</a>，\
                            这里是天天生鲜商城！</p>
                            <p>请点击站点链接完成注册确认！</p>
                            <p>此链接有效期为{}天！</p>
                            '''.format(username, '127.0.0.1:8000', token, settings.CONFIRM_DAYS)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()




























