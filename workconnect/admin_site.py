# workconnect/admin_site.py
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _


class WorkConnectAdminSite(AdminSite):
    site_header = _("WorkConnect Uganda Administration")
    site_title = _("WorkConnect Admin Portal")
    index_title = _("Welcome to WorkConnect Admin Portal")


admin_site = WorkConnectAdminSite(name='workconnect_admin')

# Register all models
from django.apps import apps
from django.contrib import admin

# Get all models
all_models = apps.get_models()

# Register models that aren't already registered
for model in all_models:
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass