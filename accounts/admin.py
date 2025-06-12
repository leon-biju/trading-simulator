# For registering models that show up in  admin page
from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cash_balance', 'created_on')
    search_fields = ('user__username',)
