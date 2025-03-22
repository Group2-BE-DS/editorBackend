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

            # Send email
            send_mail(
                subject='Collaboration Invitation',
                message=f'''Your verification code is: {code}
                \nUse this token to connect: {base64_code}
                \nRepository: {repository.slug}''',
                from_email=settings.EMAIL_HOST_USER,
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