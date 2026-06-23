from __future__ import annotations

def required_scope_for_rest_path(path: str) -> str | None:
    normalized = path.split("?", 1)[0]
    if normalized.startswith("/api/v1/entities"):
        return "entities"
    ####
    if normalized.startswith("/api/v1/tasks"):
        return "tasks"
    ####
    if normalized.startswith("/api/v1/objects"):
        return "objects"
    ####
    return None
####


def required_scope_for_grpc_method(method: str) -> str | None:
    if "EntityManagerAPI/" in method:
        return "entities"
    ####
    if "TaskManagerAPI/" in method:
        return "tasks"
    ####
    return None
####


def scope_tokens(scope: str | None) -> set[str]:
    if not scope:
        return set()
    ####
    tokens: set[str] = set()
    for raw_token in scope.replace(",", " ").split():
        token = raw_token.strip()
        if token:
            tokens.add(token)
        ####
    ####
    return tokens
####


def scope_allows(scope: str | None, required_scope: str) -> bool:
    tokens = scope_tokens(scope)
    if not tokens:
        return False
    ####
    if required_scope in tokens:
        return True
    ####
    if "*" in tokens or "all" in tokens:
        return True
    ####
    return False
####
