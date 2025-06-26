from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import (
    CustomUser, Report, ReportVote, UserQuestion, 
    LoginAttempt, UserActivity
)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Enhanced admin interface for CustomUser"""
    
    list_display = ('email', 'full_name', 'status', 'profession', 'neighborhood', 
                   'created_at', 'is_active')
    list_filter = ('status', 'profession', 'is_active', 'is_staff', 'created_at')
    search_fields = ('email', 'full_name', 'phone_number', 'neighborhood')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {
            'fields': ('full_name', 'phone_number', 'profession', 'neighborhood')
        }),
        ('Documents', {
            'fields': ('id_card', 'supporting_doc')
        }),
        ('Account Status', {
            'fields': ('status', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_admin', 
                      'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'phone_number', 'profession', 
                      'neighborhood', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login_ip')
    
    actions = ['approve_users', 'reject_users', 'suspend_users']
    
    def approve_users(self, request, queryset):
        """Approve selected users"""
        from django.utils import timezone
        updated = queryset.update(
            status=CustomUser.AccountStatus.VALIDATED,
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} users were approved.')
    approve_users.short_description = "Approve selected users"
    
    def reject_users(self, request, queryset):
        """Reject selected users"""
        updated = queryset.update(status=CustomUser.AccountStatus.REFUSED)
        self.message_user(request, f'{updated} users were rejected.')
    reject_users.short_description = "Reject selected users"
    
    def suspend_users(self, request, queryset):
        """Suspend selected users"""
        updated = queryset.update(status=CustomUser.AccountStatus.SUSPENDED)
        self.message_user(request, f'{updated} users were suspended.')
    suspend_users.short_description = "Suspend selected users"

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Admin interface for Report"""
    
    list_display = ('title', 'user', 'category', 'urgency', 'location', 
                   'vote_count', 'is_verified', 'created_at')
    list_filter = ('category', 'urgency', 'is_verified', 'is_active', 'created_at')
    search_fields = ('title', 'description', 'location', 'user__full_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Report Details', {
            'fields': ('title', 'description', 'category', 'urgency', 'location')
        }),
        ('Media', {
            'fields': ('image', 'video', 'document')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_verified', 'is_active')
        }),
        ('Metadata', {
            'fields': ('user', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'vote_count')
    
    actions = ['verify_reports', 'deactivate_reports']
    
    def verify_reports(self, request, queryset):
        """Verify selected reports"""
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} reports were verified.')
    verify_reports.short_description = "Verify selected reports"
    
    def deactivate_reports(self, request, queryset):
        """Deactivate selected reports"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} reports were deactivated.')
    deactivate_reports.short_description = "Deactivate selected reports"

@admin.register(ReportVote)
class ReportVoteAdmin(admin.ModelAdmin):
    """Admin interface for ReportVote"""
    
    list_display = ('report', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('report__title', 'user__full_name')
    ordering = ('-created_at',)

@admin.register(UserQuestion)
class UserQuestionAdmin(admin.ModelAdmin):
    """Admin interface for UserQuestion"""
    
    list_display = ('report', 'questioner', 'is_answered', 'created_at')
    list_filter = ('is_answered', 'created_at')
    search_fields = ('question', 'answer', 'report__title', 'questioner__full_name')
    ordering = ('-created_at',)

@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """Admin interface for LoginAttempt"""
    
    list_display = ('email', 'ip_address', 'success', 'timestamp')
    list_filter = ('success', 'timestamp')
    search_fields = ('email', 'ip_address')
    ordering = ('-timestamp',)
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """Admin interface for UserActivity"""
    
    list_display = ('user', 'activity_type', 'ip_address', 'timestamp')
    list_filter = ('activity_type', 'timestamp')
    search_fields = ('user__full_name', 'description', 'ip_address')
    ordering = ('-timestamp',)
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

# Customize admin site
admin.site.site_header = "Bambili Connect Administration"
admin.site.site_title = "Bambili Connect Admin"
admin.site.index_title = "Welcome to Bambili Connect Administration"

