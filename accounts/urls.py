from django.urls import path

from .views import (
    ApplicationLoginView,
    ApplicationLogoutView,
    ApplicationPasswordChangeView,
    account_list,
    account_password,
    dashboard,
    register,
    set_role,
    teacher_edit,
    teacher_list,
)

urlpatterns = [
    path("accounts/login/", ApplicationLoginView.as_view(), name="login"),
    path("accounts/logout/", ApplicationLogoutView.as_view(), name="logout"),
    path("accounts/register/", register, name="register"),
    path("dashboard/", dashboard, name="dashboard"),
    path("accounts/manage/", account_list, name="accounts"),
    path("accounts/<int:user_id>/role/", set_role, name="set_role"),
    path("accounts/<int:user_id>/password/", account_password, name="account_password"),
    path("password/change/", ApplicationPasswordChangeView.as_view(), name="password_change"),
    path("teachers/", teacher_list, name="teachers"),
    path("teachers/<int:user_id>/edit/", teacher_edit, name="teacher_edit"),
]
