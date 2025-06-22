# users/admin.py
from django.contrib import admin
from .models import UserProfile, UserRole
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

# Define an inline admin descriptor for UserProfile model
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'
    fk_name = 'user'
    fields = ('role',) # Only display the role field

# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_user_role')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'profile__role')
    search_fields = ('username', 'first_name', 'last_name', 'email') # Good to have for User search
    ordering = ('username',)

    def get_user_role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, 'profile') else 'N/A'
    get_user_role.short_description = 'Role'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(UserAdmin, self).get_inline_instances(request, obj)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# --- NEW: Register UserProfile model explicitly for autocomplete ---
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name') # Fields to search on for autocomplete
    raw_id_fields = ('user',) # Allows selecting User by ID, useful if many users
    autocomplete_fields = ['user'] # User model needs to have search_fields defined in its admin (which BaseUserAdmin does)