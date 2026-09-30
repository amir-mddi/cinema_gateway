from dataclasses import dataclass

@dataclass(frozen=True)
class RequirementResult:
    complete: bool
    missing: tuple[str, ...]


def membership_ok(payload: dict) -> bool:
    status = payload.get("status", "")
    return status in {"creator", "administrator", "member"} or (status == "restricted" and payload.get("is_member") is True)
