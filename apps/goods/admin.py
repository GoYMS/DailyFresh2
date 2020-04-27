from django.contrib import admin
from goods.models import GoodsType, IndexGoodsBanner, IndexTypeGoodsBanner, IndexPromotionBanner, GoodsSKU, Goods
# Register your models here.
from django.core.cache import cache


class BaseAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        """新增或修改数据的时候调用"""
        super().save_model(request, obj, form, change)

        # 发出任务, 让celery重新生成首页静态文件页
        # 此处不知为何必须将包倒在此处，不然会报错
        from celery_tasks.tasks import send_static_index
        send_static_index.delay()
        # 删除首页的缓存
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        """删除数据的时候调用"""
        super().save_model(request, obj)

        # 发出任务, 让celery重新生成首页静态文件页
        from celery_tasks.tasks import send_static_index
        send_static_index.delay()
        # 删除首页的缓存
        cache.delete('index_page_data')


class GoodsTypeAdmin(BaseAdmin):
    list_display = ['name', 'logo']


class IndexGoodsBannerAdmin(BaseAdmin):
    list_display = ['sku', 'index']


class IndexTypeGoodsBannerAdmin(BaseAdmin):
    list_display = ['type', 'sku']


class IndexPromotionBannerAdmin(BaseAdmin):
    list_display = ['name']


class GoodsSKUAdmin(BaseAdmin):
    list_display = ['name', 'price']


class GoodsAdmin(BaseAdmin):
    list_display = ['name', 'detail']


admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
admin.site.register(Goods, GoodsAdmin)

