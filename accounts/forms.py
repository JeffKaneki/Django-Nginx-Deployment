from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm, UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .recaptcha import verify_recaptcha

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username",
        max_length=50,
        widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def clean(self):
        if not verify_recaptcha(
            self.data.get("g-recaptcha-response", ""),
            self.request.META.get("REMOTE_ADDR"),
        ):
            raise ValidationError("Complete the I'm not a robot CAPTCHA verification and try again.")
        return super().clean()


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(max_length=255)
    phone = forms.CharField(max_length=30)
    address = forms.CharField(max_length=255)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "phone", "address")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class TeacherCreateForm(forms.ModelForm):
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "phone", "address")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.TEACHER
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class TeacherEditForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        min_length=8,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Leave blank to keep the current password.",
    )

    class Meta:
        model = User
        fields = ("username", "email", "phone", "address")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class RoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("role",)


class AdminSetPasswordForm(SetPasswordForm):
    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")
        validate_password(password, self.user)
        return password


class AccountPasswordChangeForm(PasswordChangeForm):
    pass
