from .access import organization_for


def current_organization(request):
    """Makes {{ current_org }} available in every template (used by the status bar)."""
    if not request.user.is_authenticated:
        return {}
    return {"current_org": organization_for(request.user)}
