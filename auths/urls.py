from django.urls import path
from .views import *

urlpatterns = [
    #all done
    path("signup", SignupView.as_view(), name="signup"),
    path("email-verify", Verify_Email_Signup.as_view(),name="email-verify"),
    path("login", LoginView.as_view(), name='login'),
    path("change-password", ChangePassword.as_view(), name='change_password'),
    path("forget-password", FogetPasswordView.as_view(), name="forget_password"),
    path("otp-verify", Verify_User_ForgetPassword.as_view(), name='verify_user_forget_password'),
    path("reset-password", ResetPasswordView.as_view(),name='reset_password'),
    path('google-auth', GoogleLoginView.as_view(),)
    
]
