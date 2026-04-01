
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CustomUser, OtpTable
from .serializers import *
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth import authenticate
import random
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.hashers import check_password
from .tasks import send_email_to
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.utils import timezone
from datetime import timedelta

from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from chats.tasks import sent_note_to_user


# Create your views here.

class SignupView(APIView):
    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def post(self, request):
        serializer = UsermodelSignupSerializer(data = request.data)
        email = serializer.initial_data['email']
        user = CustomUser.objects.filter(email=email).first()
        
        if user and user.is_email_verified==False:
            user.email = email
            user.set_password(serializer.initial_data['password'])
            user.full_name = serializer.initial_data['full_name']

   
            otp = f"{random.randint(0, 999999):06}"
            subject = 'Account Verification - Mealz'
            plain_message = f"""

Hello {user.full_name},
              
Thank you for registering with Mealz.

Your One-Time Password (OTP) to verify your account is: {otp}

Please do not share this OTP with anyone. It is valid for a limited time only.

If you did not request this, please ignore this email.


Best regards,  
The Mealz Team
"""

            send_email_to.delay(email= user.email, text = plain_message, subject=subject)

            current_otp, created = OtpTable.objects.get_or_create(user=user)
            current_otp.otp = otp
            current_otp.save()


            return Response({ "success": True, "message": "Your account has been created successfully."},status=status.HTTP_201_CREATED)
            




        if serializer.is_valid():
            user = serializer.save()
            print(user)
            otp = f"{random.randint(0, 999999):06}"
            subject = 'Account Verification - Mealz'
            plain_message = f"""

Hello {user.full_name},
              
Thank you for registering with Mealz.

Your One-Time Password (OTP) to verify your account is: {otp}

Please do not share this OTP with anyone. It is valid for a limited time only.

If you did not request this, please ignore this email.


Best regards,  
The Mealz Team"""

            send_email_to.delay(email= user.email, text = plain_message, subject=subject)

            current_otp, created = OtpTable.objects.get_or_create(user=user)
            current_otp.otp = otp
            current_otp.save()



            return Response({ "success": True, "message": "Your account has been created successfully."},status=status.HTTP_201_CREATED)

        return Response(
            {
                "success":False,
                "message": "An account with this email already exists.",
                                
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    

class Verify_Email_Signup(APIView):
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    def post(self,request):

        serializer = OTPSerializer(data = request.data)
        if serializer.is_valid():
            try:
                user = CustomUser.objects.get(email = serializer.validated_data.get('email'))
                otp_object = OtpTable.objects.get(user=user)

                if otp_object.otp == serializer.validated_data.get('otp'):
                    if timezone.now() - otp_object.updated_at <= timedelta(minutes=5):
                        user.is_email_verified = True
                        user.save()
                        otp_object.otp = random.randint(0,999999)
                        otp_object.save()

                        sent_note_to_user.delay(user_id=user.id, title="Congratulations!", content="Your email has been successfully verified. Welcome to Mealz", note_type='success')

                        return Response({"success":True,"message":"Your email has been successfully verified. Welcome to Mealz"}, status = status.HTTP_200_OK)
                    else:
                        return Response({"success":False,"message":"Your OTP has expired. Please request a new one to verify your email!"}, status=status.HTTP_400_BAD_REQUEST)

                else:
                    return Response({"success":False,"message":"The verification code you entered is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

            except CustomUser.DoesNotExist:
                return Response({"success":False,"message":"No account found with the provided email."},status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "success":False,
                "errors":serializer.errors
                                
            },
            status=status.HTTP_400_BAD_REQUEST
        )



class LoginView(APIView):
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    def post(self,request):
        serializer = LoginSerializers(data = request.data)
        if serializer.is_valid():
            user = authenticate(email = serializer.data['email'], password = serializer.data['password'])
            if user:
                if user.is_email_verified:
                    refresh = RefreshToken.for_user(user)

                    user_data = UsermodelSignupSerializerView(user)

                    response = Response(
                        {
                            "success": True,
                            "message": "login successful!",
                            "access": str(refresh.access_token),
                            "user":user_data.data
                        },
                        status=status.HTTP_200_OK
                    )

                    response.set_cookie(
                        key="refresh_token",
                        value=str(refresh),
                        httponly=True, 
                        secure=True,
                        samesite="Lax",
                        max_age=24 * 60 * 60*30 
                    )

                    return response
                
                otp = f"{random.randint(0, 999999):06}"
                subject = 'Account Verification - Mealz'
                plain_message = f"""

Hello {user.full_name},
              
Thank you for registering with Mealz.

Your One-Time Password (OTP) to verify your account is: {otp}

Please do not share this OTP with anyone. It is valid for a limited time only.

If you did not request this, please ignore this email.


Best regards,  
The Mealz Team
"""
                
                send_email_to.delay(email= user.email, text = plain_message, subject=subject)

                # save otp to database
                current_otp, created = OtpTable.objects.get_or_create(user=user)
                current_otp.otp = otp
                current_otp.save()
                
                return Response(
                    {
                        "success":False,
                        "message":"We sent an otp to your email! verify your first then login", 
                        
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                    
                )

            return Response({"success":False,"message":"username or password Invalid!"}, status=status.HTTP_401_UNAUTHORIZED)   
        return Response(
            {
                "success":False,
                "message": f"{str(next(iter(serializer.errors.values()))[0])}",
                                
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    

class ChangePassword(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    def post(self, request):
        user = request.user        
        serializer =  ChangePassword_serializer(data = request.data)
        if serializer.is_valid():
            hash_password = user.password
            raw_password = serializer.data['old_password']
            if check_password(raw_password, hash_password):
                user.set_password(serializer.data['new_password'])
                user.save()
                return Response({"message":"Your password has been changed successfully."}, status= status.HTTP_200_OK)
            else:
                return Response({"message":"The current password you entered is incorrect. Please try again."}, status=status.HTTP_400_BAD_REQUEST )
        return Response(
            {
                "success":False,
                "message":"All fields are required.",
                                
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    


class FogetPasswordView(APIView):
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    def post(self, request):
        serializer = ForgetPasswordSerializer(data = request.data)
        if serializer.is_valid():
            try:
                user = CustomUser.objects.get(email = serializer.validated_data['email'])

                otp = f"{random.randint(0, 999999):06}"
                subject = 'Account Verification - Mealz'
                plain_message = f"""

Hello {user.full_name},
              
Thank you for registering with Mealz.

Your One-Time Password (OTP) to verify your account is: {otp}

Please do not share this OTP with anyone. It is valid for a limited time only.

If you did not request this, please ignore this email.


Best regards,  
The Mealz Team
"""
                send_email_to.delay(email= user.email, text = plain_message, subject=subject)

                # save otp to database
                current_otp, created = OtpTable.objects.get_or_create(user=user)
                current_otp.otp = otp
                current_otp.save()

                return Response(
                    {
                        "success":True,
                        "message":"We have sent a verification code (OTP) to your email.",
                    },
                    status=status.HTTP_200_OK
                    )
            except CustomUser.DoesNotExist:
                return Response({"success":False,"message":"No account was found with the provided details."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
            {
                "success":False,
                "message": f"The email field is required.",
                                
            },
            status=status.HTTP_400_BAD_REQUEST
        )
        


class Verify_User_ForgetPassword(APIView):
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    def post(self, request):
        serializer = OTPSerializer(data = request.data)
        if serializer.is_valid():
            try:
                user = CustomUser.objects.get(email = serializer.validated_data.get('email'))

                otp_object = OtpTable.objects.get(user=user)

                if otp_object.otp == serializer.validated_data.get('otp'):
                    if timezone.now() - otp_object.updated_at <= timedelta(minutes=5):
                        user.is_email_verified = True
                        user.save()
                        otp_object.otp = random.randint(0,999999)
                        otp_object.save()


                        # then reponse
                        refresh = RefreshToken.for_user(user)
                        user_data = UsermodelSignupSerializerView(user)
                        
                        response = Response(
                            {
                                "success": True,
                                "message": "Email verified successfully!",
                                "access": str(refresh.access_token),
                                "user":user_data.data
                            },
                            status=status.HTTP_200_OK
                        )

                        response.set_cookie(
                            key="refresh_token",
                            value=str(refresh),
                            httponly=True, 
                            secure=True,
                            samesite="Lax",
                            max_age=24 * 60 * 60*30 
                        )

                        return response

      
                    else:
                        return Response({"success":False,"message":"Your OTP has expired. Please request a new one to verify your email!"}, status=status.HTTP_400_BAD_REQUEST)

                else:
                    return Response({"success":False,"message":"The verification code you entered is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
                

            except CustomUser.DoesNotExist:
                return Response({"success":False,"message":"No account was found with the provided email."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "success":False,
                "message": "The OTP field is required.",                   
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class ResetPasswordView(APIView):
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        serializer = ResetPasswordSerializer(data = request.data)
        if serializer.is_valid():
            user.set_password(serializer.data['new_password'])
            user.save()
            return Response({ "success": True, "message": "Your password has been reset successfully."}, status=status.HTTP_200_OK)
        return Response(
            {
                "success":False,
                "message": "Please provide a new password to proceed with resetting your account.",                
            },
            status=status.HTTP_400_BAD_REQUEST
        )



def generate_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "success":True,
        "message":"login success",
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        
    }

class GoogleLoginView(APIView):
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    def post(self, request):
        token = request.data.get("id_token")
        print(token)    
        try:
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request())
            email = idinfo.get("email")
            owner_name = idinfo.get("name")
            users, created = CustomUser.objects.get_or_create(email=email)
            users.first_name=owner_name
            users.defaults={"email": email}
            users.username = email
            users.is_email_verified=True
            users.save()

            refresh = RefreshToken.for_user(users)

            user_data = UsermodelSignupSerializerView(users)

            response = Response(
                {
                    "success": True,
                    "message": "login successful!",
                    "access": str(refresh.access_token),
                    "user":user_data.data
                },
                status=status.HTTP_200_OK
            )

            response.set_cookie(
                key="refresh_token",
                value=str(refresh),
                httponly=True, 
                secure=True,
                samesite="Lax",
                max_age=24 * 60 * 60*30 
            )

            return response

        except:
            return Response({"success":False,"error": "Invalid Google token"}, status=status.HTTP_400_BAD_REQUEST)

