# Create your models here.

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.base_user import BaseUserManager
from django.utils import timezone
import os

class ProfessionType(models.TextChoices):
    STUDENT = 'student', _('Student')
    TEACHER = 'teacher', _('Teacher')
    MERCHANT = 'merchant', _('Merchant')
    FARMER = 'farmer', _('Farmer')
    CIVIL_SERVANT = 'civil_servant', _('Civil Servant')
    HEALTHCARE_WORKER = 'healthcare_worker', _('Healthcare Worker')
    OTHER = 'other', _('Other')

class AccountStatus(models.TextChoices):
    PENDING = 'pending', _('Pending Approval')
    VALIDATED = 'validated', _('Validated')
    REFUSED = 'refused', _('Refused')
    SUSPENDED = 'suspended', _('Suspended')

class ReportCategory(models.TextChoices):
    ELECTRICITY = 'electricity', _('Electricity')
    WATER = 'water', _('Water')
    SHOPS = 'shops', _('Shops & Services')
    CHARGING_POINTS = 'charging_points', _('Charging Points')
    SECURITY = 'security', _('Security')
    TRANSPORT = 'transport', _('Transport')
    HEALTH = 'health', _('Health Services')
    EDUCATION = 'education', _('Education')
    OTHER = 'other', _('Other')

class UrgencyLevel(models.TextChoices):
    LOW = 'low', _('Low')
    MEDIUM = 'medium', _('Medium')
    HIGH = 'high', _('High')
    CRITICAL = 'critical', _('Critical')

def user_directory_path(instance, filename):
    """File will be uploaded to MEDIA_ROOT/user_<id>/<filename>"""
    return f'user_{instance.id}/{filename}'

def report_directory_path(instance, filename):
    """File will be uploaded to MEDIA_ROOT/reports/user_<id>/<filename>"""
    return f'reports/user_{instance.user.id}/{filename}'

class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('status', AccountStatus.VALIDATED)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        if extra_fields.get('is_admin') is not True:
            raise ValueError('Superuser must have is_admin=True.')
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    # Remove the username field as we'll use email
    username = None
    
    # Custom user fields
    full_name = models.CharField(max_length=255, help_text="Enter your full name as it appears on your ID")
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?237\d{9}$', message="Phone number must be in Cameroon format: +237XXXXXXXXX")],
        unique=True,
        help_text="Enter your phone number in format: +237XXXXXXXXX"
    )
    profession = models.CharField(
        max_length=20,
        choices=ProfessionType.choices,
        default=ProfessionType.OTHER
    )
    neighborhood = models.CharField(
        max_length=255, 
        help_text="Enter your specific neighborhood in Bambili (e.g., Mile 4, Ntarinkon, etc.)"
    )
    
    # Document uploads
    id_card = models.ImageField(
        upload_to=user_directory_path, 
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf'])],
        help_text="Upload a clear photo of your National ID card (JPG, PNG, or PDF)"
    )
    supporting_doc = models.FileField(
        upload_to=user_directory_path, 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf'])],
        help_text="Optional: Upload additional supporting document (JPG, PNG, or PDF)"
    )
    
    # Account status and metadata
    status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    
    # Admin approval fields
    approved_by = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
        related_name='approved_users'
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone_number', 'profession', 'neighborhood']
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    
    @property
    def is_verified(self):
        return self.status == AccountStatus.VALIDATED
    
    @property
    def can_post_reports(self):
        return self.is_verified and self.status != AccountStatus.SUSPENDED
    
    @property
    def get_initials(self):
        """Get user's initials from full name (max 2 characters)"""
        if not self.full_name:
            return '??'
        parts = self.full_name.split()
        initials = ''.join(part[0].upper() for part in parts if part)
        return initials[:2] if len(initials) >= 2 else (initials + '?')[:2]


    @property
    def can_vote(self):
        return self.is_verified and self.status != AccountStatus.SUSPENDED
    
    def is_verified(self):
        return self.status == AccountStatus.VALIDATED

class Report(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(help_text="Provide detailed information about the situation")
    location = models.CharField(
        max_length=255,
        help_text="Specific location within Bambili (e.g., Mile 4 Junction, Ntarinkon Market)"
    )
    category = models.CharField(
        max_length=20,
        choices=ReportCategory.choices,
        default=ReportCategory.OTHER
    )
    urgency = models.CharField(
        max_length=10, 
        choices=UrgencyLevel.choices,
        default=UrgencyLevel.LOW
    )
    
    # Geolocation
    latitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Latitude coordinate of the report location"
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Longitude coordinate of the report location"
    )
    
    # Media attachments
    image = models.ImageField(
        upload_to=report_directory_path, 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        help_text="Upload a photo as proof (JPG or PNG)"
    )
    video = models.FileField(
        upload_to=report_directory_path, 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'mov', 'avi'])],
        help_text="Upload a video as proof (MP4, MOV, or AVI)"
    )
    document = models.FileField(
        upload_to=report_directory_path, 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])],
        help_text="Upload a document as proof (PDF, DOC, or DOCX)"
    )
    
    # Geolocation (optional)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    
    # Metadata
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'created_at']),
            models.Index(fields=['location', 'created_at']),
            models.Index(fields=['is_verified', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.location}"
    
    @property
    def vote_count(self):
        return self.votes.count()
    
    @property
    def verification_threshold_met(self):
        """Check if verification threshold is met (5 votes)"""
        return self.vote_count >= 5
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('report_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        current_user = kwargs.pop('current_user', None)
        # Correction : on ne touche pas aux relations si l'objet n'a pas encore d'ID
        if self.pk is None:
            super().save(*args, **kwargs)
            return
        if current_user and current_user.is_admin:
            pass  # Admin peut forcer la vérification
        else:
            self.is_verified = self.verification_threshold_met
        super().save(*args, **kwargs)

class ReportVote(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='votes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'report')
        indexes = [
            models.Index(fields=['report', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} voted for {self.report.title}"

class UserQuestion(models.Model):
    """Model for users to ask questions about reports"""
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='questions')
    questioner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='questions_asked')
    question = models.TextField()
    answer = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(blank=True, null=True)
    is_answered = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Question about {self.report.title} by {self.questioner.full_name}"

class LoginAttempt(models.Model):
    """Model to track login attempts for security monitoring"""
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    success = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['email', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
        ]

class UserActivity(models.Model):
    """Model to track user activities for monitoring"""
    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('report_created', 'Report Created'),
        ('report_updated', 'Report Updated'),
        ('vote_cast', 'Vote Cast'),
        ('question_asked', 'Question Asked'),
        ('profile_updated', 'Profile Updated'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['activity_type', 'timestamp']),
        ]

