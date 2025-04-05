import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from difflib import unified_diff

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Configuration
API_KEY = "#"  # Replace with your actual API key or set GEMINI_API_KEY env variable
MODEL_NAME = "gemini-1.5-pro"  # Verify this is a valid model
PROJECT_CONFIG_FILE = ".codegenrc"

class CodeGenerationSystem:
    def __init__(self, api_key: str = API_KEY, model_name: str = MODEL_NAME):
        self.api_key = api_key
        self.model_name = model_name
        self.config = self._load_project_config()
        self._initialize_model()
        
    def _initialize_model(self):
        """Initialize the Gemini model."""
        genai.configure(api_key=self.api_key)
        
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE, 
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
        }
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            safety_settings=self.safety_settings,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )
    
    def _load_project_config(self) -> Dict:
        """Load project configuration from .codegenrc file."""
        config_path = Path(PROJECT_CONFIG_FILE)
        return json.load(open(config_path, 'r')) if config_path.exists() else {
            "code_style": "clean",
            "documentation_style": "google",
            "user_preferences": {},
            "file_patterns": {
                "python": "*.py", "javascript": "*.js", "typescript": "*.ts",
                "java": "*.java", "c": "*.c", "cpp": ["*.cpp", "*.cc", "*.h", "*.hpp"],
                "csharp": "*.cs"
            },
            "context_depth": 3,
            "max_tokens_per_file": 4096
        }
    
    def _extract_code_blocks(self, file_path: Path) -> Dict:
        """Extract code blocks and comments from a file."""
        if not file_path.exists():
            return {"content": "", "blocks": [], "todos": [], "language": "unknown"}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        extension = file_path.suffix.lower()
        language = self._get_language_from_extension(extension)
        
        blocks, todos = {
            "python": self._parse_python_file,
            "javascript": self._parse_js_ts_file,
            "typescript": self._parse_js_ts_file,
            "java": self._parse_c_style_file,
            "c": self._parse_c_style_file,
            "cpp": self._parse_c_style_file,
            "csharp": self._parse_c_style_file
        }.get(language, lambda x: ([], []))(content)
        
        return {"content": content, "blocks": blocks, "todos": todos, "language": language}
    
    def _get_language_from_extension(self, extension: str) -> str:
        """Get programming language from file extension."""
        return {
            ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript",
            ".jsx": "javascript", ".java": "java", ".c": "c", ".cpp": "cpp", ".cc": "cpp",
            ".h": "c", ".hpp": "cpp", ".cs": "csharp"
        }.get(extension, "unknown")
    
    def _parse_python_file(self, content: str) -> Tuple[List[Dict], List[Dict]]:
        """Parse Python file to extract code blocks and TODOs."""
        blocks, todos, lines = [], [], content.split('\n')
        current_block = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "# @generate" in stripped:
                current_block = {"start_line": i, "marker": stripped.split("# @generate", 1)[1].strip(), "content": []}
            elif current_block and stripped == "# @end":
                current_block["end_line"] = i
                blocks.append(current_block)
                current_block = None
            elif current_block:
                current_block["content"].append(line)
            if "# TODO:" in stripped:
                todos.append({"line": i, "text": stripped.split("# TODO:", 1)[1].strip()})
        
        return blocks, todos
    
    def _parse_js_ts_file(self, content: str) -> Tuple[List[Dict], List[Dict]]:
        """Parse JavaScript/TypeScript file to extract code blocks and TODOs."""
        blocks, todos, lines = [], [], content.split('\n')
        current_block = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "// @generate" in stripped:
                current_block = {"start_line": i, "marker": stripped.split("// @generate", 1)[1].strip(), "content": []}
            elif current_block and stripped == "// @end":
                current_block["end_line"] = i
                blocks.append(current_block)
                current_block = None
            elif current_block:
                current_block["content"].append(line)
            if "// TODO:" in stripped:
                todos.append({"line": i, "text": stripped.split("// TODO:", 1)[1].strip()})
        
        return blocks, todos
    
    def _parse_c_style_file(self, content: str) -> Tuple[List[Dict], List[Dict]]:
        """Parse C-style languages file to extract code blocks and TODOs."""
        blocks, todos, lines = [], [], content.split('\n')
        current_block = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "// @generate" in stripped:
                current_block = {"start_line": i, "marker": stripped.split("// @generate", 1)[1].strip(), "content": []}
            elif current_block and stripped == "// @end":
                current_block["end_line"] = i
                blocks.append(current_block)
                current_block = None
            elif current_block:
                current_block["content"].append(line)
            if "// TODO:" in stripped:
                todos.append({"line": i, "text": stripped.split("// TODO:", 1)[1].strip()})
            elif "/* TODO:" in stripped:
                todo_text = stripped.split("/* TODO:", 1)[1].strip()
                if "*/" in todo_text:
                    todo_text = todo_text.split("*/", 1)[0].strip()
                todos.append({"line": i, "text": todo_text})
        
        return blocks, todos
    
    def _find_related_files(self, file_path: Path, max_files: int = 3) -> List[Dict]:
        """Find related files in the repository based on imports and references."""
        related_files, directory, extension = [], file_path.parent, file_path.suffix
        files_in_dir = list(directory.glob(f"*{extension}"))
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return related_files
            
        language = self._get_language_from_extension(extension)
        imported_files = []
        
        if language == "python":
            for line in content.split('\n'):
                if line.strip().startswith(("import ", "from ")):
                    parts = line.replace("import ", "").replace("from ", "").split()
                    if parts:
                        module_name = parts[0].split('.')[0]
                        potential_file = directory / f"{module_name}.py"
                        if potential_file.exists():
                            imported_files.append(potential_file)
        
        for imp_file in imported_files:
            if imp_file != file_path and len(related_files) < max_files:
                file_info = self._extract_code_blocks(imp_file)
                file_info["path"] = str(imp_file)
                related_files.append(file_info)
        
        for f in files_in_dir:
            if f != file_path and f not in imported_files and len(related_files) < max_files:
                file_info = self._extract_code_blocks(f)
                file_info["path"] = str(f)
                related_files.append(file_info)
                
        return related_files
    
    def _build_prompt(self, file_path: Path, file_info: Dict, related_files: List[Dict], user_input: Optional[str] = None) -> str:
        """Build a prompt for the LLM based on file content and context."""
        prompt = f"""You are an expert software developer tasked with generating high-quality code.

CURRENT FILE: {file_path}
LANGUAGE: {file_info['language']}

USER PREFERENCES:
- Code style: {self.config.get("code_style", "clean")}
- Documentation style: {self.config.get("documentation_style", "google")}
"""
        if user_input:
            prompt += f"\nUSER REQUEST:\n{user_input}\n"
        else:
            prompt += """
\nUSER REQUEST:
No specific user input provided. Generate or enhance the code in the current file by leveraging the context from related files in the same directory (e.g., database utilities, configurations, or other service files). Focus on implementing or improving functionality based on the current file's TODOs, generation markers, and the related files' content.
"""
            
        user_prefs = self.config.get("user_preferences", {})
        if user_prefs:
            prompt += "\nADDITIONAL USER PREFERENCES:\n" + "\n".join(f"- {k}: {v}" for k, v in user_prefs.items()) + "\n"
                
        prompt += f"\nCURRENT FILE CONTENT:\n```{(file_info['language'])}\n{file_info['content']}\n```\n"
        
        if file_info["todos"]:
            prompt += "\nTODOs IN CURRENT FILE:\n" + "\n".join(f"- Line {t['line']}: {t['text']}" for t in file_info["todos"]) + "\n"
                
        if file_info["blocks"]:
            prompt += "\nCODE GENERATION BLOCKS:\n"
            for block in file_info["blocks"]:
                block_content = '\n'.join(block['content'])
                prompt += f"- Lines {block['start_line']}-{block['end_line']}: {block['marker']}\n"
                prompt += f"```{file_info['language']}\n{block_content}\n```\n"
                
        if related_files:
            prompt += "\nRELATED FILES FOR CONTEXT:\n"
            for idx, rel_file in enumerate(related_files):
                prompt += f"\n### RELATED FILE {idx+1}: {rel_file['path']}\n"
                prompt += f"```{rel_file['language']}\n{rel_file['content'][:1000]}{'...' if len(rel_file['content']) > 1000 else ''}\n```\n"
                
        prompt += """
INSTRUCTIONS:
1. Generate or update code based on the context, user preferences, and any TODO comments or generation markers.
2. If no user input is provided, use the content of related files to infer and implement missing functionality (e.g., database interactions, configurations, or service logic).
3. Provide comprehensive code that fits the project's style and follows best practices.
4. Include appropriate documentation and comments.
5. If responding to a specific code generation block, ensure your code can directly replace the content between the markers.
6. Explain your implementation choices.

RESPONSE FORMAT:
- Begin with a brief summary of what you're generating and why
- Provide the complete implementation in a code block
- Add insights explaining the code's design, patterns used, and any important considerations

Output should be organized, well-documented, and ready for direct integration into the codebase.
"""
        return prompt
    
    def _compare_code(self, old_code: str, new_code: str) -> str:
        """Compare old and new code and return a diff."""
        old_lines = old_code.splitlines()
        new_lines = new_code.splitlines()
        diff = unified_diff(old_lines, new_lines, fromfile="Previous Code", tofile="Generated Code", lineterm="")
        return "\n".join(diff)
    
    def _generate_justification(self, old_code: str, new_code: str, user_input: Optional[str], file_info: Dict) -> str:
        """Generate a justification for why the new code was created."""
        justification = "Justification for Code Generation:\n"
        
        if not old_code.strip():
            justification += "- The previous code was empty or non-existent, so the new code was generated to fulfill the user request or TODOs.\n"
        elif user_input:
            justification += f"- The new code was generated in response to the user request: '{user_input}'.\n"
        else:
            justification += "- No user input was provided; the new code was generated by leveraging related files in the same directory to implement or enhance functionality.\n"
        
        if file_info["todos"]:
            justification += "- Addressed TODOs found in the original file:\n" + "\n".join(f"  - {t['text']}" for t in file_info["todos"]) + "\n"
        
        if file_info["blocks"]:
            justification += "- Modified or implemented code within generation blocks:\n" + "\n".join(f"  - {b['marker']}" for b in file_info["blocks"]) + "\n"
        
        diff_lines = self._compare_code(old_code, new_code).splitlines()
        if diff_lines:
            justification += "- Key changes made:\n"
            for line in diff_lines[:10]:
                if line.startswith("+") and not line.startswith("+++"):
                    justification += f"  - Added: {line[1:].strip()}\n"
                elif line.startswith("-") and not line.startswith("---"):
                    justification += f"  - Removed: {line[1:].strip()}\n"
            if len(diff_lines) > 10:
                justification += "  - (Additional changes omitted for brevity; see full diff for details)\n"
        
        return justification
    
    def generate_code_for_file(self, file_path: str, user_input: Optional[str] = None) -> Dict:
        """Generate code for a specific file with optional user input, including comparison and justification."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                "success": False,
                "message": f"File {file_path} does not exist.",
                "code": None,
                "insights": None,
                "diff": None,
                "justification": None
            }
            
        file_info = self._extract_code_blocks(file_path)
        related_files = self._find_related_files(file_path, max_files=self.config.get("context_depth", 3))
        prompt = self._build_prompt(file_path, file_info, related_files, user_input)
        original_code = file_info["content"]
        
        try:
            response = self.model.generate_content(prompt)
            result = self._parse_generation_response(response.text)
            
            diff = self._compare_code(original_code, result["code"])
            justification = self._generate_justification(original_code, result["code"], user_input, file_info)
            
            return {
                "success": True,
                "message": "Code generation successful",
                "code": result["code"],
                "insights": result["insights"],
                "diff": diff,
                "justification": justification,
                "file_path": str(file_path)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error generating code: {str(e)}",
                "code": None,
                "insights": None,
                "diff": None,
                "justification": None
            }
    
    def _parse_generation_response(self, response_text: str) -> Dict:
        """Parse LLM response to extract code and insights."""
        result = {"code": "", "insights": ""}
        code_blocks, insights_text, in_code_block, current_block = [], [], False, []
        
        for line in response_text.split('\n'):
            if line.startswith("```"):
                if in_code_block:
                    in_code_block = False
                    code_blocks.append('\n'.join(current_block))
                    current_block = []
                else:
                    in_code_block = True
                    continue
            elif in_code_block:
                current_block.append(line)
            else:
                insights_text.append(line)
        
        result["code"] = '\n\n'.join(code_blocks)
        result["insights"] = '\n'.join(insights_text)
        return result
    
    def update_file_with_generated_code(self, file_path: str, generated_code: str, block_index: Optional[int] = None) -> Dict:
        """Update a file with generated code, either replacing a specific block or the entire file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"success": False, "message": f"File {file_path} does not exist."}
            
        file_info = self._extract_code_blocks(file_path)
        
        try:
            if block_index is not None and 0 <= block_index < len(file_info["blocks"]):
                block = file_info["blocks"][block_index]
                lines = file_info["content"].split('\n')
                new_lines = lines[:block["start_line"] + 1] + generated_code.split('\n') + lines[block["end_line"]:]
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                return {"success": True, "message": f"Updated block {block_index} in {file_path}"}
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(generated_code)
                return {"success": True, "message": f"Updated entire file {file_path}"}
        except Exception as e:
            return {"success": False, "message": f"Error updating file: {str(e)}"}