import os
from pathlib import Path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

BASE_DIR = Path(__file__).resolve().parent.parent  # Project root
FILE_ROOT = BASE_DIR / 'user_files'  # Directory for user files

class FileSystemView(APIView):
    def get(self, request, path=''):
        """
        List files and directories or read file content.
        """
        target_path = FILE_ROOT / path

        if target_path.is_dir():
            items = [
                {
                    'name': item.name,
                    'is_dir': item.is_dir(),
                }
                for item in target_path.iterdir()
            ]
            return Response({'items': items})
        elif target_path.is_file():
            with open(target_path, 'r') as file:
                content = file.read()
            return Response({'content': content})
        else:
            return Response({'error': 'Path not found'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, path=''):
        """
        Create a file or directory.
        """
        target_path = FILE_ROOT / path
        data = request.data

        if data.get('is_dir', False):
            target_path.mkdir(parents=True, exist_ok=True)
            return Response({'message': 'Directory created'})
        else:
            with open(target_path, 'w') as file:
                file.write(data.get('content', ''))
            return Response({'message': 'File created'})

    def put(self, request, path=''):
        """
        Update an existing file.
        """
        target_path = FILE_ROOT / path

        if target_path.is_file():
            with open(target_path, 'w') as file:
                file.write(request.data.get('content', ''))
            return Response({'message': 'File updated'})
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
