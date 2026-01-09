from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v2/", include([
        path("auth/", include("apps.accounts.urls")),
        path("product/", include("apps.products.urls")),
        path("cart/", include("apps.cart.urls")),
        path("review/", include("apps.reviews.urls")),
        path("wishlist/", include("apps.wishlist.urls")),
        path("order/", include("apps.orders.urls")),
    ])),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
