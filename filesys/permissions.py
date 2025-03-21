from rest_framework import permissions

class IsOwnerOrCollaborator(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Allow read operations for collaborators
        if request.method in permissions.SAFE_METHODS:
            return obj.user_has_access(request.user)
        
        # Write operations only for owner
        return obj.user == request.user