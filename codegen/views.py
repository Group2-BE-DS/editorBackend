from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .codegen import CodeGenerationSystem
from django.conf import settings
import os
import google.generativeai as genai

API_KEY = os.environ.get("GEMINI_API_KEY", "#")
MODEL_NAME = "gemini-2.0-flash"

@api_view(['POST'])
def generate_code(request):
    """API endpoint to generate code for a given file."""
    try:
        # Extract data from the request
        data = request.data
        file_path = data.get('file_path')
        user_input = data.get('user_input', None)
        block_index = data.get('block_index', None)
        save_to_file = data.get('save_to_file', False)

        if not file_path:
            return JsonResponse({"success": False, "message": "file_path is required"}, status=400)

        # Initialize the code generation system
        system = CodeGenerationSystem(api_key=API_KEY, model_name=MODEL_NAME)

        # Generate code
        result = system.generate_code_for_file(file_path, user_input)

        if not result["success"]:
            return JsonResponse(result, status=500)

        # Save the generated code if requested
        if save_to_file:
            update_result = system.update_file_with_generated_code(
                file_path, 
                result["code"], 
                block_index
            )
            result["file_update"] = update_result

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({
            "success": False, 
            "message": f"Error processing request: {str(e)}"
        }, status=500)

class GenerateDocsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, repo_slug):
        """Generate documentation for a repository"""
        try:
            # Get repository path from request data
            repo_path = request.data.get('repo_path')
            if not repo_path:
                return JsonResponse({
                    'success': False,
                    'message': 'repo_path is required in request body'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Clean up and normalize the provided repo_path
            repo_path = os.path.abspath(os.path.normpath(repo_path))
            
            # Validate repo path exists
            if not os.path.exists(repo_path):
                return JsonResponse({
                    'success': False,
                    'message': f'Repository path not found: {repo_path}'
                }, status=status.HTTP_404_NOT_FOUND)

            # Initialize Gemini
            genai.configure(api_key=API_KEY)
            model = genai.GenerativeModel(MODEL_NAME)

            # Get all files in repository
            file_contents = []
            for root, _, files in os.walk(repo_path):
                for file in files:
                    if file.endswith(('.py', '.js', '.ts', '.html', '.css', '.md')):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                file_contents.append({
                                    'path': os.path.relpath(file_path, repo_path),
                                    'content': content[:1000]  # First 1000 chars
                                })
                        except Exception as e:
                            print(f"Error reading {file_path}: {e}")

            # Prepare prompt for documentation generation
            prompt = f"""
            Generate comprehensive documentation for this repository.
            Create a complete README.md including:
            - Project Overview
            - Technologies Used
            - Setup Instructions
            - Project Structure
            - Usage Examples
            - API Documentation (if applicable)
            - Contributing Guidelines
            
            Repository Files:
            {chr(10).join([f'- {f["path"]}:{chr(10)}```{chr(10)}{f["content"]}{chr(10)}```' for f in file_contents])}
            
            Return ONLY the markdown content for README.md without any additional text.
            """

            # Generate documentation
            response = model.generate_content(prompt)
            generated_content = response.text

            # Save README.md
            readme_path = os.path.join(repo_path, 'README.md')
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(generated_content)

            return JsonResponse({
                'success': True,
                'message': 'Documentation generated successfully',
                'content': generated_content,
                'file_path': readme_path
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error generating documentation: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)