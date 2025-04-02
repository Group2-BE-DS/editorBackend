from django.shortcuts import render
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .tasks import commit_to_main
from filesys.models import Repository
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def commit_to_main_branch(request, repository_slug):
    """
    API endpoint to commit changes to the main branch using repository slug
    """
    logger.info(f"Request received: {request.method} {request.path}")
    logger.info(f"User: {request.user.username}")
    logger.info(f"Repository slug: {repository_slug}")
    logger.info(f"Request headers: {request.headers}")
    logger.info(f"Request body: {request.body}")
    
    try:
        # Log all repositories for debugging
        all_repos = Repository.objects.all()
        logger.info(f"Available repositories: {[repo.slug for repo in all_repos]}")
        
        repository = Repository.objects.get(slug=repository_slug)
        logger.info(f"Found repository: {repository.name} (slug: {repository.slug})")
        
        # Check if user has access to repository
        if repository.user != request.user:
            logger.error(f"User {request.user.username} does not have access to repository {repository_slug}")
            return Response(
                {"message": "You don't have permission to access this repository"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        success = commit_to_main(repository.id)
        if success:
            logger.info(f"Successfully committed changes to main branch for {repository_slug}")
            return Response(
                {"message": "Successfully committed changes to main branch"},
                status=status.HTTP_200_OK
            )
        logger.info(f"No changes to commit for {repository_slug}")
        return Response(
            {"message": "No changes to commit"},
            status=status.HTTP_200_OK
        )
    except Repository.DoesNotExist:
        logger.error(f"Repository not found with slug: {repository_slug}")
        return Response(
            {"error": f"Repository not found with slug: {repository_slug}"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return Response(
            {"error": "An unexpected error occurred", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
