from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from .models import Report, ReportVote, CustomUser
from .forms import ReportForm

from django.urls import reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

class ReportDetailView(DetailView):
    model = Report
    template_name = 'trustwave/report_detail.html'
    context_object_name = 'report'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_vote'] = self.request.user.is_verified and not self.request.user.is_admin
        context['has_voted'] = ReportVote.objects.filter(
            user=self.request.user,
            report=self.object
        ).exists()
        return context

@login_required
@require_POST
def vote_report(request, report_id):
    """
    Handle voting on a report
    Only verified users can vote
    """
    if not request.user.is_verified:
        messages.error(request, 'Only verified users can vote on reports')
        return redirect('trustwave:report_list')
    
    report = get_object_or_404(Report, pk=report_id)
    user = request.user
    
    # Check if user has already voted
    if ReportVote.objects.filter(user=user, report=report).exists():
        messages.error(request, 'You have already voted on this report')
        return redirect('trustwave:report_list')
    
    # Create new vote
    ReportVote.objects.create(user=user, report=report)
    
    # Update report vote count and save
    report.vote_count = report.votes.count()
    report.save()  # This will trigger the save() method that verifies the report
    
    # Return simple success message
    return JsonResponse({
        'success': True,
        'voted': True,
        'vote_count': report.vote_count,
        'message': 'Vote added'
    })

@require_POST
@login_required
@csrf_protect
def toggle_report_like(request, report_id):
    """
    Toggle like status for a report
    """
    report = get_object_or_404(Report, pk=report_id)
    user = request.user
    
    # Check if user has already liked this report
    if ReportVote.objects.filter(user=user, report=report).exists():
        # Remove like
        ReportVote.objects.filter(user=user, report=report).delete()
        liked = False
    else:
        # Add like
        ReportVote.objects.create(user=user, report=report)
        liked = True
    
    # Update report's vote count
    report.vote_count = report.votes.count()
    report.save()
    
    return JsonResponse({
        'success': True,
        'liked': liked,
        'vote_count': report.vote_count
    })
from django_ratelimit.decorators import ratelimit
import json
import logging
import folium
from folium import plugins

from .models import (
    CustomUser, Report, ReportVote, UserQuestion, 
    LoginAttempt, UserActivity, ReportCategory, AccountStatus
)
from .forms import (
    SecureRegistrationForm, SecureLoginForm, ReportForm, 
    UserQuestionForm, ProfileUpdateForm
)

# Set up logging
logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_user_activity(user, activity_type, description, request):
    """Log user activity for monitoring"""
    UserActivity.objects.create(
        user=user,
        activity_type=activity_type,
        description=description,
        ip_address=get_client_ip(request)
    )

def home(request):
    """Home page view with statistics"""
    context = {
        'total_users': CustomUser.objects.filter(status='validated').count(),
        'total_reports': Report.objects.filter(is_active=True).count(),
        'verified_reports': Report.objects.filter(is_verified=True, is_active=True).count(),
        'active_today': UserActivity.objects.filter(
            timestamp__date=timezone.now().date()
        ).values('user').distinct().count(),
        'recent_reports': Report.objects.filter(
            is_active=True
        ).select_related('user').order_by('-created_at')[:6]
    }
    return render(request, 'trustwave/index.html', context)

@ratelimit(key='ip', rate='5/m', method='POST')
def register_view(request):
    """User registration view with rate limiting"""
    if request.user.is_authenticated:
        return redirect('trustwave:dashboard')
    
    if request.method == 'POST':
        form = SecureRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            
            # Log registration attempt
            LoginAttempt.objects.create(
                email=user.email,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True
            )
            
            messages.success(
                request, 
                'Registration successful! Your account is pending admin approval. '
                'You will receive an email once approved.'
            )
            logger.info(f"New user registered: {user.email}")
            return redirect('trustwave:registration_pending')
        else:
            # Log failed registration
            email = request.POST.get('email', 'unknown')
            LoginAttempt.objects.create(
                email=email,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=False
            )
    else:
        form = SecureRegistrationForm()
    
    return render(request, 'trustwave/register.html', {'form': form})

@ratelimit(key='ip', rate='10/m', method='POST')
def login_view(request):
    """User login view with rate limiting"""
    if request.user.is_authenticated:
        return redirect('trustwave:dashboard')
    
    if request.method == 'POST':
        form = SecureLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Update last login IP
            user.last_login_ip = get_client_ip(request)
            user.save(update_fields=['last_login_ip'])
            
            # Log successful login
            log_user_activity(user, 'login', 'User logged in', request)
            LoginAttempt.objects.create(
                email=user.email,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True
            )
            
            messages.success(request, f'Welcome back, {user.full_name}!')
            logger.info(f"User logged in: {user.email}")
            
            # Redirect to next page or dashboard
            next_page = request.GET.get('next', 'trustwave:dashboard')
            return redirect(next_page)
        else:
            # Log failed login
            email = request.POST.get('username', 'unknown')
            LoginAttempt.objects.create(
                email=email,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=False
            )
    else:
        form = SecureLoginForm()
    
    return render(request, 'trustwave/login.html', {'form': form})

@login_required
def logout_view(request):
    """User logout view"""
    user = request.user
    log_user_activity(user, 'logout', 'User logged out', request)
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('trustwave:home')

def registration_pending(request):
    """Registration pending approval page"""
    return render(request, 'trustwave/registration_pending.html')

@login_required
def dashboard(request):
    """User dashboard view"""
    user = request.user
    
    # Get user's reports
    user_reports = Report.objects.filter(user=user).order_by('-created_at')[:5]
    
    # Get user's statistics
    stats = {
        'total_reports': Report.objects.filter(user=user).count(),
        'verified_reports': Report.objects.filter(user=user, is_verified=True).count(),
        'total_votes_received': ReportVote.objects.filter(report__user=user).count(),
        'questions_received': UserQuestion.objects.filter(report__user=user).count(),
    }
    
    # Get recent activities
    recent_activities = UserActivity.objects.filter(user=user).order_by('-timestamp')[:10]
    
    context = {
        'user_reports': user_reports,
        'stats': stats,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'trustwave/dashboard.html', context)

@login_required
def profile_view(request):
    """User profile view"""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            log_user_activity(request.user, 'profile_updated', 'User updated profile', request)
            messages.success(request, 'Profile updated successfully!')
            return redirect('trustwave:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'trustwave/profile.html', {'form': form})

class ReportListView(ListView):
    """List all reports with filtering and pagination"""
    model = Report
    template_name = 'trustwave/report_list.html'
    context_object_name = 'reports'
    paginate_by = 12
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_categories'] = ReportCategory.choices
        return context
    
    def get_queryset(self):
        queryset = Report.objects.filter(is_active=True).select_related('user').order_by('-created_at')
        
        # Filter by category
        category = self.request.GET.get('category')
        if category and category in dict(ReportCategory.choices):
            queryset = queryset.filter(category=category)
        
        # Filter by verification status
        verified = self.request.GET.get('verified')
        if verified == 'true':
            queryset = queryset.filter(is_verified=True)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ReportCategory.choices
        context['current_category'] = self.request.GET.get('category', '')
        context['current_search'] = self.request.GET.get('search', '')
        context['current_verified'] = self.request.GET.get('verified', '')
        return context

class ReportDetailView(DetailView):
    """Detailed view of a single report"""
    model = Report
    template_name = 'trustwave/report_detail.html'
    context_object_name = 'report'
    
    def get_queryset(self):
        return Report.objects.filter(is_active=True).select_related('user')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = self.get_object()
        
        # Check if user has voted
        if self.request.user.is_authenticated:
            context['user_has_voted'] = ReportVote.objects.filter(
                user=self.request.user, report=report
            ).exists()
        
        # Get questions and answers
        context['questions'] = UserQuestion.objects.filter(
            report=report
        ).select_related('questioner').order_by('-created_at')
        
        # Question form
        if self.request.user.is_authenticated and self.request.user.is_verified:
            context['question_form'] = UserQuestionForm()
        
        return context

@login_required
@ratelimit(key='user', rate='5/m', method='POST')
def submit_report(request):
    """Nouvelle vue simplifiée pour soumettre un rapport"""
    if not request.user.can_post_reports:
        messages.error(request, 'You need to be a verified user to submit reports.')
        return redirect('trustwave:dashboard')

    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.save()  # Les fichiers et coordonnées sont déjà gérés par le ModelForm
            messages.success(request, 'Votre rapport a bien été enregistré !')
            return redirect('trustwave:submit_report')
        else:
            # Afficher les erreurs du formulaire via messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            messages.error(request, "Please correct the errors below and try again.")
    else:
        form = ReportForm()

    return render(request, 'trustwave/submit_report.html', {
        'form': form,
        'can_submit': request.user.can_post_reports
    })

@login_required
@require_POST
@ratelimit(key='user', rate='10/m', method='POST')
def vote_report(request, report_id):
    """Vote on a report (AJAX endpoint)"""
    if not request.user.can_vote:
        return JsonResponse({
            'success': False, 
            'message': 'You need to be a verified user to vote.'
        })
    
    try:
        report = get_object_or_404(Report, id=report_id, is_active=True)
        
        # Check if user already voted
        vote, created = ReportVote.objects.get_or_create(
            user=request.user,
            report=report
        )
        
        if not created:
            # Remove vote if already exists
            vote.delete()
            voted = False
            message = 'Vote removed'
        else:
            voted = True
            message = 'Vote added'
            log_user_activity(
                request.user, 
                'vote_cast', 
                f'Voted on report: {report.title}', 
                request
            )
        
        # Update report verification status
        vote_count = report.vote_count
        if vote_count >= 5 and not report.is_verified:
            report.is_verified = True
            report.save(update_fields=['is_verified'])
        
        return JsonResponse({
            'success': True,
            'voted': voted,
            'vote_count': vote_count,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error voting on report {report_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while voting.'
        })

@login_required
@require_POST
@ratelimit(key='user', rate='5/m', method='POST')
def ask_question(request, report_id):
    """Ask a question about a report"""
    if not request.user.is_verified:
        messages.error(request, 'You need to be a verified user to ask questions.')
        return redirect('report_detail', pk=report_id)
    
    report = get_object_or_404(Report, id=report_id, is_active=True)
    form = UserQuestionForm(request.POST)
    
    if form.is_valid():
        question = form.save(commit=False)
        question.report = report
        question.questioner = request.user
        question.save()
        
        log_user_activity(
            request.user, 
            'question_asked', 
            f'Asked question about report: {report.title}', 
            request
        )
        
        messages.success(request, 'Question submitted successfully!')
    else:
        messages.error(request, 'Please correct the errors in your question.')
    
    return redirect('report_detail', pk=report_id)

def map_view(request):
    """Interactive map view showing all reports"""
    # Get all active reports with geolocation
    reports = Report.objects.filter(
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False
    ).select_related('user')
    
    # Prepare map data
    map_reports = []
    for report in reports:
        map_reports.append({
            'id': report.id,
            'title': report.title,
            'description': report.description,
            'location': report.location,
            'category': report.category,
            'urgency': report.urgency,
            'is_verified': report.is_verified,
            'latitude': float(report.latitude),
            'longitude': float(report.longitude),
            'created_at': report.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'vote_count': report.vote_count,
            'detail_url': reverse('trustwave:report_detail', kwargs={'pk': report.id})
        })
    
    # Prepare context
    context = {
        'reports': reports,
        'map_reports': map_reports,  # Données JSON sérialisables
        'can_post_reports': request.user.can_post_reports if request.user.is_authenticated else False,
        'recent_reports': Report.objects.filter(is_active=True).order_by('-created_at')[:5]
    }
    
    return render(request, 'trustwave/map_view.html', context)

@staff_member_required
def admin_dashboard(request):
    """Admin dashboard for managing users and reports"""
    print("Hello")
   
    # Get users by status
    pending_users = CustomUser.objects.filter(status='pending').order_by('-created_at')
    validated_users = CustomUser.objects.filter(status='validated').order_by('-created_at')
    refused_users = CustomUser.objects.filter(status='refused').order_by('-created_at')
    
    # Get recent reports
    recent_reports = Report.objects.filter(is_active=True).order_by('-created_at')[:10]
    
    # Get statistics
    stats = {
        'pending_users': pending_users.count(),
        'total_users': validated_users.count(),
        'total_reports': Report.objects.filter(is_active=True).count(),
        'flagged_reports': Report.objects.filter(is_active=False).count(),
    }
    
    context = {
        'pending_users': pending_users,
        'validated_users': validated_users,
        'refused_users': refused_users,
        'recent_reports': recent_reports,
        'stats': stats,
        'all_users': CustomUser.objects.all().order_by('-created_at'),
    }
    
    return render(request, 'trustwave/admin_dashboard.html', context)

@staff_member_required
def validate_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    user.status = AccountStatus.VALIDATED
    user.approved_by = request.user
    user.approved_at = timezone.now()
    user.save()
    
    # Log the activity
    log_user_activity(
        request.user, 
        'user_validated', 
        f'Validated user {user.full_name} (ID: {user.id})',
        request
    )
    
    messages.success(request, f"{user.full_name}'s account has been validated.")
    return redirect('trustwave:admin_dashboard')

@staff_member_required
def refuse_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        user.status = AccountStatus.REFUSED
        user.rejection_reason = rejection_reason
        user.save()
        
        # Log the activity
        log_user_activity(
            request.user, 
            'user_refused', 
            f'Refused user {user.full_name} (ID: {user.id}). Reason: {rejection_reason}',
            request
        )
        
        messages.info(request, f"{user.full_name}'s account has been refused.")
        return redirect('trustwave:admin_dashboard')
    
    # If GET request, show confirmation page
    context = {'user': user}
    return render(request, 'trustwave/refuse_user_confirm.html', context)

@staff_member_required
def view_user_documents(request, user_id):
    """View user documents for verification"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    context = {
        'user': user,
    }
    
    return render(request, 'trustwave/view_user_documents.html', context)

# Error handlers
def custom_404(request, exception):
    """Custom 404 error page"""
    return render(request, 'trustwave/404.html', status=404)

def custom_500(request):
    """Custom 500 error page"""
    return render(request, 'trustwave/500.html', status=500)

@staff_member_required
@login_required
def verify_report(request, report_id):
    """Verify or unverify a report - admins can override verification status"""
    report = get_object_or_404(Report, pk=report_id)
    
    if request.method == 'POST':
        verification_status = request.POST.get('verification_status')
        if verification_status == 'verified':
            report.is_verified = True
            messages.success(request, f'Report has been verified')
        elif verification_status == 'pending':
            report.is_verified = False
            messages.success(request, f'Report is now pending verification')
        report.save(current_user=request.user)
        return redirect('trustwave:report_detail', pk=report_id)
    
    context = {
        'report': report,
        'current_status': 'verified' if report.is_verified else 'pending'
    }
    return render(request, 'trustwave/verify_report.html', context)
    
    context = {
        'report': report,
        'current_status': 'verified' if report.is_verified else 'pending'
    }

