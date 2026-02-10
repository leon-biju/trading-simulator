# mypy: disable-error-code=type-arg

# For registering models that show up in  admin page
from django.contrib import admin
from .models import CustomUser, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_on', 'home_currency')
    search_fields = ('user__username',)

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    search_fields = ('username', 'email')