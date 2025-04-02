from django.http import JsonResponse
from rest_framework.decorators import api_view
from .codegen import CodeGenerationSystem
import os

API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyB8FunrHdiub5Xsp7PaploytkC0XzUlS8k")
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