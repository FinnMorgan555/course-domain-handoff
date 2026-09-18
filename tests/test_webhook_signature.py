import hashlib
import hmac

from course_domain_service.webhook_security import valid_signature


def test_verification_event_signature_is_checked() -> None:
    body = b'{"type":"dns.domain.verified","data":{"domain":"learn.school.example"}}'
    digest = hmac.new(b"local-secret", body, hashlib.sha256).hexdigest()

    assert valid_signature(body, f"sha256={digest}", "local-secret")
    assert not valid_signature(body, "sha256=changed", "local-secret")
