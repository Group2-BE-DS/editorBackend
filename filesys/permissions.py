from rest_framework import permissions

class IsOwnerOrCollaborator(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # For read operations, check if user is owner or collaborator
        if request.method in permissions.SAFE_METHODS:
            return obj.user_has_access(request.user)

        # For write operations, check if user is owner
        if hasattr(obj, 'repository'):  # File object
            return obj.repository.user == request.user
        return obj.user == request.user  # Repository object