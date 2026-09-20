from django.urls import path
from apps.user.api.views import auth

urlpatterns = [

    path('login/',auth.LoginMobileView.as_view()),
    path('verify/',auth.VerifyCodeView.as_view())

]
