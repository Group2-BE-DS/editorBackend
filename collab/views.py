from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from .serializers import VerificationCodeSerializer
from filesys.models import Repository
from django.shortcuts import get_object_or_404
from .token_store import TokenStore
import base64
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
            emails = serializer.validated_data['emails']

            # Generate verification code
            code = ''.join(random.choices(string.digits, k=8))
            code_bytes = code.encode('ascii')
            base64_code = base64.b64encode(code_bytes).decode('ascii')

            # Store token with repository info
            TokenStore.add_token(base64_code, repository.slug)

            # HTML email template
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
                        <h3 style="margin: 0 0 10px 0;">Your Verification Code</h3>
                        <div style="font-size: 24px; font-weight: bold; letter-spacing: 2px;">{base64_code}</div>
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

            # Plain text version for email clients that don't support HTML
            text_content = f"""
            Collaboration Invitation

            You've been invited to collaborate on the repository: {repository.slug}

            Your verification code is: {code}
            Token to connect: {base64_code}

            Please do not reply to this email.
            """

            # Send email with both HTML and plain text versions
            send_mail(
                subject='C.C.C - Collaboration Invitation',
                message=text_content,
                html_message=html_content,
                from_email=f'C.C.C <{settings.EMAIL_HOST_USER}>',  # Using a friendly from name
                recipient_list=emails,
                fail_silently=False,
            )

            return Response({
                'message': 'Verification code sent successfully',
                'code': base64_code,
                'repository_slug': repository.slug
            })

        except Repository.DoesNotExist:
            return Response({
                'detail': 'Repository not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)