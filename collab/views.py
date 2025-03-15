from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
import base64
import random
import string
from .token_store import TokenStore

class VerificationCodeAPI(APIView):
    def post(self, request):
        # Get emails from request data
        emails = request.data.get('emails', [])
        if not isinstance(emails, list):
            emails = [emails]

        if not emails:
            return Response(
                {'error': 'No email addresses provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate 8-digit code
        code = ''.join(random.choices(string.digits, k=8))
        
        # Convert to base64
        code_bytes = code.encode('ascii')
        base64_code = base64.b64encode(code_bytes).decode('ascii')

        # Store the token
        TokenStore.add_token(base64_code)

        try:
            # Send email to all recipients
            send_mail(
                subject='Your Verification Code',
                message=f'Your verification code is: {code}\n\nUse this token to connect: {base64_code}',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=emails,
                fail_silently=False,
            )

            return Response({
                'message': 'Verification code sent successfully',
                'code': base64_code
            }, status=status.HTTP_200_OK)

        except Exception as e:
            TokenStore.remove_token(base64_code)
            return Response({
                'error': f'Failed to send email: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
