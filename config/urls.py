from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/', include('market.urls')),
    path('api/', include('trading.urls')),
    path('api/', include('wallets.urls')),
    # SPA catch-all: serve index.html for any non-api path.
    re_path(
        r'^(?!api/|admin/|static/|media/).*$',
        TemplateView.as_view(template_name='index.html'),
        name='spa',
    ),
]
