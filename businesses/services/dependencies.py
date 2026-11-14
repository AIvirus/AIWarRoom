"""Rules for the component dependency graph."""


def creates_cycle(component, proposed_dependencies) -> bool:
    """
    Would `component` depending on `proposed_dependencies` create a loop?

    A loop (A needs B, B needs C, C needs A) makes failure propagation meaningless, so we
    refuse it. We walk "downhill" from each proposed dependency through what *it* depends
    on; if we ever reach `component` again, the new edge would close a circle.
    """
    target_id = component.pk
    to_visit = [dep.pk for dep in proposed_dependencies]
    seen = set()
    # Imported here so this module stays importable without app loading (tests, shell).
    from businesses.models import BusinessComponent

    while to_visit:
        current = to_visit.pop()
        if current == target_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        to_visit.extend(
            BusinessComponent.depends_on.through.objects.filter(
                from_businesscomponent_id=current
            ).values_list("to_businesscomponent_id", flat=True)
        )
    return False
