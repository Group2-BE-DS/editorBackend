from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
import base64
import random
import string
from .token_store import TokenStore
from filesys.models import Repository

class VerificationCodeAPI(APIView):
    def post(self, request):
        # Get emails and repository info from request data
        emails = request.data.get('emails', [])
        repository_id = request.data.get('repository_id')
        
        if not isinstance(emails, list):
            emails = [emails]

        if not emails:
            return Response(
                {'error': 'No email addresses provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get repository slug
        repository = get_object_or_404(Repository, id=repository_id)
        repo_slug = repository.slug

        # Generate 8-digit code
        code = ''.join(random.choices(string.digits, k=8))
        
        # Convert to base64
        code_bytes = code.encode('ascii')
        base64_code = base64.b64encode(code_bytes).decode('ascii')

        # Store the token with repository ID
        TokenStore.add_token(base64_code)

        try:
            # Send email to all recipients
            send_mail(
                subject='Collaboration Invitation',
                message=f'''Your verification code is: {code}
                \nUse this token to connect: {base64_code}
                \nRepository: {repo_slug}''',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=emails,
                fail_silently=False,
            )

            return Response({
                'message': 'Verification code sent successfully',
                'code': base64_code,
                'repository_id': repository_id,
                'repository_slug': repo_slug
            }, status=status.HTTP_200_OK)

        except Exception as e:
            TokenStore.remove_token(base64_code)
            return Response({
                'error': f'Failed to send email: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
