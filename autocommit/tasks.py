import os
import git
import logging
from django.conf import settings
from filesys.models import Repository

logger = logging.getLogger(__name__)

def auto_commit_changes(repository_id):
    """
    Automatically commit changes for a specific repository
    Args:
        repository_id: ID of the repository being accessed
    """
    try:
        repository = Repository.objects.get(id=repository_id)
        repo_path = repository.location
        
        if not os.path.exists(repo_path):
            logger.warning(f"Repository path does not exist: {repo_path}")
            return
            
        repo = git.Repo(repo_path)
        changed_files = get_changed_files(repo)

        if changed_files:
            try:
                # Stage all changes
                repo.git.add(A=True)
                
                # Generate commit message with file details
                commit_message = generate_commit_message(changed_files)
                
                # Create commit
                commit = repo.index.commit(commit_message)
                
                # Update repository last commit hash
                repository.last_commit_hash = commit.hexsha
                repository.save()
                
                logger.info(f"✅ Created commit in {repo_path}: {commit_message}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to create commit: {str(e)}")
                return False
        else:
            logger.info(f"No changes detected in {repo_path}")
            return False
            
    except Repository.DoesNotExist:
        logger.error(f"Repository with ID {repository_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error during auto-commit: {str(e)}")
        return False

def get_changed_files(repo):
    """Returns a list of changed and untracked files"""
    try:
        # Get changed tracked files
        changed = [item.a_path for item in repo.index.diff(None)]
        # Get untracked files
        untracked = repo.untracked_files
        return changed + untracked
    except Exception as e:
        logger.error(f"Error getting changed files: {str(e)}")
        return []

def generate_commit_message(changed_files):
    """Generate descriptive commit message based on changes"""
    if not changed_files:
        return "chore: no changes detected"
        
    # Group files by type/extension
    file_types = {}
    for file in changed_files:
        ext = os.path.splitext(file)[1].lower() or 'no_extension'
        if ext not in file_types:
            file_types[ext] = []
        file_types[ext].append(file)
    
    # Create detailed message
    message = f"chore: auto-commit {len(changed_files)} file(s)\n\n"
    for ext, files in file_types.items():
        message += f"\n{ext} files changed:"
        for f in files:
            message += f"\n- {f}"
            
    return message