from django.db import models

# filepath: c:\Users\Yashwant Padelkar\Documents\GitHub\editorBackend\filesys\tasks.py
import os
import git
import logging
from celery import shared_task
from filesys.models import Repository

logger = logging.getLogger(__name__)

@shared_task
def auto_commit_task():
    """Automatically commit changes in all repositories."""
    repositories = Repository.objects.all()
    for repo in repositories:
        try:
            if not os.path.exists(repo.location):
                logger.warning(f"Repository path does not exist: {repo.location}")
                continue

            repo_git = git.Repo(repo.location)
            changed_files = get_changed_files(repo_git)

            if changed_files:
                # Stage all changes (tracked & untracked)
                repo_git.git.add(A=True)

                # Generate commit message
                commit_message = f"Auto-commit: {len(changed_files)} file(s) updated."

                # Commit 
                repo_git.index.commit(commit_message)
                logger.info(f" Committed in {repo.location}: {commit_message}")
            else:
                logger.info(f"No changes detected in {repo.location}.")
        except Exception as e:
            logger.error(f" Error in repository {repo.location}: {e}")

def get_changed_files(repo):
    """Returns a list of changed and untracked files for a given repository."""
    changed = [item.a_path for item in repo.index.diff(None)]
    untracked = repo.untracked_files
    return changed + untracked


