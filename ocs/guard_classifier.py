"""
Zeya #25 guard classifier — the single authoritative predicate.

``guard_classify(text, policy)`` is used in two ways:

1. Host-side, imported directly:
   ``validate_output_policy`` calls it on each fixed referral to ensure the
   referral itself does not contain content the guard would block.

2. Embedded in the generated OCS CodeNode:
   ``render_output_guard`` reads this function's source via ``inspect.getsource``
   and inlines it inside ``main``.  The same code path runs at runtime inside the
   RestrictedPython sandbox.

There is therefore ONE predicate, not two similar implementations.

Sandbox constraints (the function must satisfy both host and node execution):
  - All imports are inside the function body.
  - ``re`` is the only import used (``urllib`` is not on the sandbox allow-list).
  - URL canonicalisation is implemented with pure ``re``.
  - No ``urllib``, no file I/O, no network, no credentials.
  - The function is a plain ``def``, no decorators.

URL canonicalisation policy:
  - Scheme is lowercased (genuinely case-insensitive).
  - Host is lowercased (genuinely case-insensitive per RFC 3986 §3.2.2).
  - Path and query are preserved exactly (case-sensitive).
  - Meaningful path slashes are preserved: ``/approved`` and ``/approved/``
    require separate explicit approval.
  - Fragment identifiers (#...) are discarded on both sides.
  - Trailing punctuation that is clearly not part of the URL (.,;:!?')> ) is
    stripped from the detected URL only.
  - Non-HTTPS URLs (http://, ftp://, www. without scheme) are always blocked.
  - Credentials (user:pass@) in the authority are always blocked.

Scope limits (do not remove; finite vocabulary pending clinical review):
  - Medicine patterns: conservative starter set, protocol list not supplied.
  - Sheng slang not covered; no equivalences asserted without a source.
  - Unicode hostname lookalikes not caught.
  - Short helpline set finite and review-pending.
  - ZW normalisation covers six specific chars; not exhaustive.
"""


def guard_classify(text, policy):
    """Classify text against the guard policy.

    Parameters
    ----------
    text : str
        The AI/card output or fixed referral text to classify.
    policy : dict
        A validated policy dict from load_output_policy.  All required keys
        must be present; this function does not re-validate the schema.

    Returns
    -------
    dict with keys ``blocked`` (bool) and ``reason`` (str).
        ``blocked`` is True if the text should be blocked.
        ``reason`` is a short non-sensitive code; ``"PASS"`` when not
        blocked, otherwise: ``empty_output``, ``too_long``, ``never_say``,
        ``medicine_name``, ``dose_pattern``, ``diagnosis_wording``,
        ``suspicious_url``, ``unverified_phone``, ``url_with_credentials``,
        ``unverified_url``.
    """
    import re  # noqa: PLC0415

    # ------------------------------------------------------------------
    # 0. Zero-width character normalisation
    # Strips U+200B ZWSP, U+200C ZWNJ, U+200D ZWJ, U+2060 WJ,
    # U+FEFF BOM/ZWNBSP, U+00AD soft-hyphen before all pattern checks.
    # ------------------------------------------------------------------
    t = re.sub("[\u200b\u200c\u200d\u2060\ufeff\u00ad]", "", text if text is not None else "")

    # 1. Empty / whitespace
    if not t.strip():
        return {"blocked": True, "reason": "empty_output"}

    # 2. Word count (fail-closed on > max_words)
    if len(t.split()) > policy["max_words"]:
        return {"blocked": True, "reason": "too_long"}

    # 3. Never-say patterns
    for pat in policy["never_say_patterns"]:
        if re.search(pat, t, re.IGNORECASE):
            return {"blocked": True, "reason": "never_say"}

    # 4. Medicine / drug name check
    for pat in policy["medicine_patterns"]:
        if re.search(pat, t, re.IGNORECASE):
            return {"blocked": True, "reason": "medicine_name"}

    # 5. Dose / dosage pattern
    for pat in policy["dose_patterns"]:
        if re.search(pat, t, re.IGNORECASE):
            return {"blocked": True, "reason": "dose_pattern"}

    # 6. Diagnostic wording
    for pat in policy["diagnosis_patterns"]:
        if re.search(pat, t, re.IGNORECASE):
            return {"blocked": True, "reason": "diagnosis_wording"}

    # 7. Suspicious URL patterns (always blocked; not allowlist-checked)
    # Covers hxxps://, ftp/data/js schemes, Markdown links, URL shorteners,
    # bare domain references and credential-bearing URLs.
    for pat in policy["suspicious_url_patterns"]:
        if re.search(pat, t, re.IGNORECASE):
            return {"blocked": True, "reason": "suspicious_url"}

    # 8. Short helpline / emergency number check (finite set; review-pending)
    # Emergency response text bypasses this guard on its own pipeline branch.
    for pat in policy["short_helpline_patterns"]:
        for num in re.findall(pat, t):
            digits = re.sub(r"\D", "", num)
            phone_ok = any(re.sub(r"\D", "", str(v)) == digits for v in policy["verified_phone_allowlist"])
            if not phone_ok:
                return {"blocked": True, "reason": "unverified_phone"}

    # 9. Long-format phone check (9-15 digits)
    # () added to separator class for international formats +1 (202) 555-0100.
    # Negative lookahead/lookbehind prevents partial match inside overlong
    # digit sequences (e.g. a 20-digit batch reference number).
    for raw in re.findall(r"(?<!\d)\+?\d[\d\s\-\.\(\)]{7,15}\d(?!\d)", t):
        digits = re.sub(r"\D", "", raw)
        if len(digits) < 9 or len(digits) > 15:
            continue
        phone_ok = any(re.sub(r"\D", "", str(v)) == digits for v in policy["verified_phone_allowlist"])
        if not phone_ok:
            return {"blocked": True, "reason": "unverified_phone"}

    # 10. URL check
    # Canonicalisation: lowercase scheme+host only; preserve path/query case;
    # preserve path slashes; strip fragment and trailing punctuation.
    # Only https:// URLs are ever allowable; non-HTTPS is always blocked.

    def gcanon(raw):
        """Return canonical URL string or None for non-HTTPS / malformed."""
        # Strip common trailing punctuation not part of URL
        url = re.sub(r"[.,;:!?)>'\"]+$", "", raw)
        # Discard fragment
        frag = url.find("#")
        if frag != -1:
            url = url[:frag]
        # Parse: require https:// scheme
        m = re.match(r"^(https://)([^/?#]*)(/[^?#]*)?(\?.*)?$", url, re.IGNORECASE)
        if not m:
            return None
        host = m.group(2).lower()  # host: case-insensitive -> lowercase
        if not host or "@" in host:  # reject empty host or credentials
            return None
        path = m.group(3) or ""
        query = m.group(4) or ""
        return "https://" + host + path + query

    for raw_url in re.findall(r"(?:https?://|www\.)[^\s]+", t, re.IGNORECASE):
        canon = gcanon(raw_url)
        if canon is None:
            # Non-HTTPS or malformed (includes www. without https://)
            return {"blocked": True, "reason": "unverified_url"}
        # Exact allowlist match against canonicalised entry
        allowed = False
        for entry in policy["verified_url_allowlist"]:
            ec = gcanon(str(entry))
            if ec is not None and canon == ec:
                allowed = True
                break
        if not allowed:
            return {"blocked": True, "reason": "unverified_url"}

    return {"blocked": False, "reason": "PASS"}
