from rest_framework import permissions


class IsEmployer(permissions.BasePermission):
    message = "사업주(인력사무소) 계정만 사용할 수 있습니다."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "employer" and hasattr(u, "company"))


class IsWorker(permissions.BasePermission):
    message = "근로자 계정만 사용할 수 있습니다."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "worker")
