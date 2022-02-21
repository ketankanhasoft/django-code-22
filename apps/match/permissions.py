from django.db.models import Q
from rest_framework import permissions

from .models import Match


class MatchPermission(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        has_perm = super(MatchPermission, self).has_permission(request, view)
        if has_perm:
            return Match.objects.filter(
                Q(id=request.resolver_match.kwargs.get("match_id", ""))
                & Q(Q(company__user=request.user) | Q(applier__user=request.user))
                & Q(status__gte=2)
            ).exists()
        return False
