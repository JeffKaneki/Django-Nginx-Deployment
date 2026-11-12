from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .forms import (
    AccountPasswordChangeForm,
    AdminSetPasswordForm,
    LoginForm,
    RegistrationForm,
    RoleForm,
    TeacherCreateForm,
    TeacherEditForm,
)

User = get_user_model()
MANAGERS = {User.Role.ADMIN, User.Role.SUPERADMIN}


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            user = request.user
            if user.role != User.Role.SUPERADMIN and user.role not in roles:
                messages.error(request, "You do not have permission to access that page.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


class ApplicationLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recaptcha_site_key"] = settings.RECAPTCHA_SITE_KEY
        return context


class ApplicationLogoutView(LogoutView):
    http_method_names = ["post", "options"]


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.role = User.Role.USER
        user.save()
        messages.success(request, "Account created. Please log in.")
        return redirect("login")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    return render(request, "accounts/dashboard.html", {"profile": request.user})


@role_required(*MANAGERS)
def account_list(request):
    accounts = User.objects.order_by("username")
    return render(request, "accounts/accounts.html", {"accounts": accounts})


@require_POST
@role_required(*MANAGERS)
def set_role(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target.pk == request.user.pk:
        messages.error(request, "You cannot change your own role.")
        return redirect("accounts")

    form = RoleForm(request.POST, instance=target)
    if not request.user.role == User.Role.SUPERADMIN:
        form.fields["role"].choices = [
            choice for choice in User.Role.choices if choice[0] != User.Role.SUPERADMIN
        ]
    if form.is_valid():
        form.save()
        messages.success(request, f"Role updated for {target.username}.")
    else:
        messages.error(request, "Select a valid role.")
    return redirect("accounts")


@role_required(*MANAGERS)
def teacher_list(request):
    form = TeacherCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        teacher = form.save()
        messages.success(request, f"Teacher account for {teacher.username} created.")
        return redirect("teachers")
    teachers = User.objects.filter(role=User.Role.TEACHER).order_by("username")
    return render(request, "accounts/teachers.html", {"form": form, "teachers": teachers})


@role_required(*MANAGERS)
def teacher_edit(request, user_id):
    teacher = get_object_or_404(User, pk=user_id, role=User.Role.TEACHER)
    form = TeacherEditForm(request.POST or None, instance=teacher)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Teacher account updated successfully.")
        return redirect("teachers")
    return render(request, "accounts/edit_teacher.html", {"form": form, "teacher": teacher})


@role_required(User.Role.SUPERADMIN)
def account_password(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target.pk == request.user.pk:
        messages.error(request, "Use the password change form to update your own password.")
        return redirect("accounts")
    form = AdminSetPasswordForm(target, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Password updated for {target.username}.")
        return redirect("accounts")
    return render(request, "accounts/account_password.html", {"form": form, "target": target})


class ApplicationPasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change.html"
    form_class = AccountPasswordChangeForm
    success_url = reverse_lazy("password_change")

    def form_valid(self, form):
        messages.success(self.request, "Your password was updated.")
        return super().form_valid(form)
