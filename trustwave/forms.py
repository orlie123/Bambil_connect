from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
import bleach
from .models import (
    CustomUser, Report, UserQuestion, ReportCategory, UrgencyLevel, ProfessionType
)

class SecureRegistrationForm(UserCreationForm):
    """Secure user registration form with enhanced validation"""
    
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name as it appears on your ID',
            'required': True,
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'required': True,
        })
    )
    
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+237XXXXXXXXX',
            'pattern': r'^\+?237\d{9}$',
            'required': True,
        })
    )
    
    profession = forms.ChoiceField(
        choices=ProfessionType.choices,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True,
        })
    )
    
    neighborhood = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Mile 4, Ntarinkon, etc.',
            'required': True,
        })
    )
    
    id_card = forms.ImageField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,.pdf',
            'required': True,
        })
    )
    
    supporting_doc = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,.pdf',
        })
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter a strong password (min 12 characters)',
            'required': True,
        })
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'required': True,
        })
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ('full_name', 'email', 'phone_number', 'profession', 'neighborhood', 
                 'id_card', 'supporting_doc', 'password1', 'password2')
    
    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name')
        if full_name:
            # Sanitize input
            full_name = bleach.clean(full_name, tags=[], strip=True)
            if len(full_name.strip()) < 2:
                raise ValidationError("Full name must be at least 2 characters long.")
        return full_name
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            # Remove any spaces or special characters except +
            phone_number = ''.join(c for c in phone_number if c.isdigit() or c == '+')
            if not phone_number.startswith('+237'):
                phone_number = '+237' + phone_number.lstrip('+').lstrip('237')
            if CustomUser.objects.filter(phone_number=phone_number).exists():
                raise ValidationError("A user with this phone number already exists.")
        return phone_number
    
    def clean_neighborhood(self):
        neighborhood = self.cleaned_data.get('neighborhood')
        if neighborhood:
            # Sanitize input
            neighborhood = bleach.clean(neighborhood, tags=[], strip=True)
        return neighborhood
    
    def clean_id_card(self):
        id_card = self.cleaned_data.get('id_card')
        if id_card:
            # Check file size (max 5MB)
            if id_card.size > 5 * 1024 * 1024:
                raise ValidationError("ID card file size must be less than 5MB.")
        return id_card

class SecureLoginForm(AuthenticationForm):
    """Secure login form with enhanced validation"""
    
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'required': True,
            'autocomplete': 'email',
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'required': True,
            'autocomplete': 'current-password',
        })
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            # Sanitize username (email)
            username = bleach.clean(username, tags=[], strip=True)
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )
            if self.user_cache is None:
                raise ValidationError("Invalid email or password.")
            else:
                self.confirm_login_allowed(self.user_cache)
        
        return self.cleaned_data
    
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError("This account is inactive.")
        if hasattr(user, 'status') and user.status == 'suspended':
            raise ValidationError("This account has been suspended.")

class ReportForm(forms.ModelForm):
    """Form for creating and updating reports"""
    
    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter a clear, descriptive title',
            'required': True,
        })
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Provide detailed information about the situation...',
            'required': True,
        })
    )
    
    location = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Mile 4 Junction, Ntarinkon Market',
            'required': True,
        })
    )
    
    category = forms.ChoiceField(
        choices=ReportCategory.choices,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True,
        })
    )
    
    urgency = forms.ChoiceField(
        choices=UrgencyLevel.choices,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True,
        })
    )
    
    image = forms.ImageField(
        required=False,
        label="Upload a photo (JPG or PNG)",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        })
    )
    
    video = forms.FileField(
        required=False,
        label="Upload a video (MP4, MOV, or AVI)",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'video/*',
        })
    )
    
    document = forms.FileField(
        required=False,
        label="Upload a document (PDF, DOC, or DOCX)",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx',
        })
    )
    
    latitude = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput()
    )
    longitude = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    class Meta:
        model = Report
        fields = ['title', 'description', 'location', 'category', 'urgency', 
                 'image', 'video', 'document', 'latitude', 'longitude']
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title:
            # Sanitize input
            title = bleach.clean(title, tags=[], strip=True)
            if len(title.strip()) < 5:
                raise ValidationError("Title must be at least 5 characters long.")
        return title
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description:
            # Sanitize input but allow basic formatting
            allowed_tags = ['p', 'br', 'strong', 'em', 'u']
            description = bleach.clean(description, tags=allowed_tags, strip=True)
            if len(description.strip()) < 20:
                raise ValidationError("Description must be at least 20 characters long.")
        return description
    
    def clean_location(self):
        location = self.cleaned_data.get('location')
        if location:
            # Sanitize input
            location = bleach.clean(location, tags=[], strip=True)
        return location
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("Image file size must be less than 5MB.")
        return image
    
    def clean_video(self):
        video = self.cleaned_data.get('video')
        if video:
            # Check file size (max 20MB)
            if video.size > 20 * 1024 * 1024:
                raise ValidationError("Video file size must be less than 20MB.")
        return video
    
    def clean_document(self):
        document = self.cleaned_data.get('document')
        if document:
            # Check file size (max 5MB)
            if document.size > 5 * 1024 * 1024:
                raise ValidationError("Document file size must be less than 5MB.")
        return document

class UserQuestionForm(forms.ModelForm):
    """Form for asking questions about reports"""
    
    question = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ask a question about this report...',
            'required': True,
        })
    )
    
    class Meta:
        model = UserQuestion
        fields = ['question']
    
    def clean_question(self):
        question = self.cleaned_data.get('question')
        if question:
            # Sanitize input
            question = bleach.clean(question, tags=[], strip=True)
            if len(question.strip()) < 10:
                raise ValidationError("Question must be at least 10 characters long.")
        return question

class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile"""
    
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'required': True,
        })
    )
    
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'pattern': r'^\+?237\d{9}$',
            'required': True,
        })
    )
    
    profession = forms.ChoiceField(
        choices=ProfessionType.choices,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True,
        })
    )
    
    neighborhood = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'required': True,
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ['full_name', 'phone_number', 'profession', 'neighborhood']
    
    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name')
        if full_name:
            full_name = bleach.clean(full_name, tags=[], strip=True)
        return full_name
    
    def clean_neighborhood(self):
        neighborhood = self.cleaned_data.get('neighborhood')
        if neighborhood:
            neighborhood = bleach.clean(neighborhood, tags=[], strip=True)
        return neighborhood

