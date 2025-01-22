import os
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Repository
from .serializers import RepositorySerializer
from django.contrib.auth.models import User

@api_view(['POST'])
def CreateRepository(request):
    if request.method == 'POST':
        repo_name = request.data.get('name')
        repo_description = request.data.get('description')

        if not repo_name or not repo_description:
            return Response(
                {"detail": "Both 'name' and 'description' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Hardcoding the user for testing purposes
        try:
            user = User.objects.get(username='mj')  # Replace 'mj' with your hardcoded username
        except User.DoesNotExist:
            return Response(
                {"detail": "Hardcoded user 'mj' does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Construct the folder path
        folder_path = f"/c3/{user.username}/{repo_name}"

        # Ensure the path exists or create it
        try:
            os.makedirs(folder_path, exist_ok=True)
        except Exception as e:
            return Response(
                {"detail": f"Failed to create folder: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Save repository information with the location
        data = {
            "name": repo_name,
            "description": repo_description,
            "user": user.id,
            "location": folder_path,  # Add the folder path to the data
        }
        serializer = RepositorySerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
