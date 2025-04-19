from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from .serializers import VerificationCodeSerializer
from filesys.models import Repository
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .token_store import TokenStore
import random
import string

class VerificationCodeAPI(APIView):
    def post(self, request):
        serializer = VerificationCodeSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'detail': 'Invalid data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            repository = get_object_or_404(
                Repository, 
                slug=serializer.validated_data['repoSlug']
            )
            usernames = serializer.validated_data['usernames']

            # Get User model and add creator to collaborators list
            User = get_user_model()
            creator = request.user
            all_usernames = list(set(usernames + [creator.username]))
            users = User.objects.filter(username__in=all_usernames)
            
            if not users:
                return Response({
                    'detail': 'No valid users found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Get users' emails
            emails = [user.email for user in users]
            
            # First add users as collaborators
            for user in users:
                repository.collaborators.add(user)
            repository.save()

            # Generate a 12-character token using URL-safe characters
            token = ''.join(random.choices(
                string.ascii_letters + string.digits + '-_',  # URL-safe characters
                k=12
            ))

            # Store token with repository info
            if not TokenStore.add_token(token, repository.slug):
                repository.collaborators.remove(*users)  # Rollback collaborator changes
                return Response({
                    'detail': 'Failed to store collaboration token'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Verify token was stored
            if not TokenStore.verify_token(token):
                TokenStore.remove_token(token)
                repository.collaborators.remove(*users)  # Rollback collaborator changes
                return Response({
                    'detail': 'Failed to verify stored token'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Send email notification
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Collaboration Invitation</title>
            </head>
            <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 40px;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #3B82F6; margin: 0;">C.C.C</h1>
                        <p style="color: #666; margin-top: 10px;">Collaborative Code Companion</p>
                    </div>
                    
                    <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 30px;">
                        <h2 style="color: #1e293b; margin-top: 0;">Collaboration Invitation</h2>
                        <p style="color: #475569; line-height: 1.6;">
                            You've been invited to collaborate on the repository: <strong>{repository.slug}</strong>
                        </p>
                    </div>

                    <div style="background-color: #3B82F6; color: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 30px;">
                        <h3 style="margin: 0 0 10px 0;">Your Collaboration Code</h3>
                        <div style="font-size: 24px; font-weight: bold; letter-spacing: 2px;">{token}</div>
                    </div>

                    <div style="border-top: 1px solid #e2e8f0; padding-top: 20px; margin-top: 20px;">
                        <p style="color: #64748b; font-size: 14px; text-align: center;">
                            This is an automated message. Please do not reply to this email.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Collaboration Invitation

            You've been invited to collaborate on the repository: {repository.slug}
            Your collaboration code: {token}

            Use this code to join the collaboration session.
            Please do not reply to this email.
            """

            # Send email with notifications
            send_mail(
                subject='C.C.C - Collaboration Invitation',
                message=text_content,
                html_message=html_content,
                from_email=f'C.C.C <{settings.EMAIL_HOST_USER}>',
                recipient_list=emails,
                fail_silently=False,
            )

            return Response({
                'message': 'Collaboration setup successful',
                'code': token,
                'repository_slug': repository.slug,
                'added_collaborators': list(users.values_list('username', flat=True))
            })

        except Repository.DoesNotExist:
            return Response({
                'detail': 'Repository not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyUserAPI(APIView):
    def get(self, request, username):
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
            return Response({
                'exists': True,
                'username': user.username
            })
        except User.DoesNotExist:
            return Response({
                'exists': False,
                'detail': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

class VerifyCodeAPI(APIView):
    def get(self, request, code):
        try:
            # The code is already URL-safe base64, no need to decode URL encoding
            decoded_code = code.strip()  # Remove any whitespace

            # Verify token exists and is valid
            if TokenStore.verify_token(decoded_code):
                repo_slug = TokenStore.get_repository_slug(decoded_code)
                if not repo_slug:
                    return Response({
                        'valid': False,
                        'detail': 'Repository not found for token'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
                return Response({
                    'valid': True,
                    'repository_slug': repo_slug
                })
            else:
                return Response({
                    'valid': False,
                    'detail': 'Invalid or expired verification code'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'valid': False,
                'detail': f'Error validating code: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)