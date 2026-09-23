"""Explicit context profiles; never silently fall back to a different schema."""


def project_context(profile: str, *, state=None, policy=None, **inputs):
    if profile == "compact":
        if state is not None or policy is not None:
            raise ValueError("Compact context takes explicit facts, catalog and budget")
        from .compact import build_context
        return build_context(**inputs)
    if profile not in {"conservative", "rich"}:
        raise ValueError("Unknown context profile")
    if state is None:
        raise ValueError("WorldState required for this context profile")
    if profile == "conservative":
        from .conservative import ContextProjector
        return ContextProjector(state, policy).build(**inputs)
    from .rich import RichContextBuilder
    return RichContextBuilder(state, policy).build(**inputs)
