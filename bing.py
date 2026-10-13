
#!/usr/bin/env python3
"""Simple interactive IndexNow URL submission tool."""

import json
import re
import socket
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

API_URL = "https://api.indexnow.org/indexnow"
TIMEOUT = 20
MAX_URLS = 10_000
USER_AGENT = "IndexNow-CLI/3.0"


class ValidationError(Exception):
    pass


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def opener():
    return urllib.request.build_opener(NoRedirectHandler())


def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError as exc:
        raise ValidationError("Input ended unexpectedly.") from exc


def normalize_site(value):
    value = value.strip()

    if "://" not in value:
        value = "https://" + value

    try:
        p = urlsplit(value)
        host = p.hostname
        port = p.port
    except ValueError as exc:
        raise ValidationError(f"Invalid website URL: {exc}") from exc

    if p.scheme.lower() != "https":
        raise ValidationError("The website must use HTTPS.")

    if not host or p.username or p.password:
        raise ValidationError("Enter a valid website hostname.")

    if port not in (None, 443):
        raise ValidationError("Only the default HTTPS port is supported.")

    if p.path not in ("", "/") or p.query or p.fragment:
        raise ValidationError(
            "Enter only the website origin, e.g. https://example.com"
        )

    try:
        host = host.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValidationError("Invalid website hostname.") from exc

    if len(host) > 253 or "." not in host:
        raise ValidationError("Enter a valid public domain name.")

    for label in host.split("."):
        if (
            not label
            or len(label) > 63
            or not re.fullmatch(
                r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label
            )
        ):
            raise ValidationError("Invalid website hostname format.")

    if not re.search(r"[a-z]", host.rsplit(".", 1)[-1]):
        raise ValidationError("Invalid domain ending.")

    return f"https://{host}", host


def validate_key(key):
    if not re.fullmatch(r"[A-Za-z0-9-]{8,128}", key):
        raise ValidationError(
            "Invalid key. Use 8-128 letters, numbers, or hyphens."
        )


def check_dns(host):
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValidationError(
            f"DNS lookup failed for {host}: {exc}"
        ) from exc


def get_key_location(site, host):
    default_location = f"{site}/{KEY}.txt"
    print(f"\nDefault key file: {default_location}")
    custom = ask("Custom key file URL (press Enter for default): ")

    if not custom:
        return default_location

    try:
        p = urlsplit(custom)
        port = p.port
    except ValueError as exc:
        raise ValidationError(f"Invalid key file URL: {exc}") from exc

    if (
        p.scheme.lower() != "https"
        or not p.hostname
        or p.hostname.lower() != host
        or p.username
        or p.password
        or port not in (None, 443)
        or p.query
        or p.fragment
        or not p.path.startswith("/")
        or p.path.endswith("/")
    ):
        raise ValidationError(
            "The key file must be an HTTPS file URL on the same hostname."
        )

    return f"https://{host}{p.path}"


def verify_key_file(location, key):
    request = urllib.request.Request(
        location,
        headers={"User-Agent": USER_AGENT},
    )

    try:
        with opener().open(request, timeout=TIMEOUT) as response:
            if response.status != 200:
                raise ValidationError(
                    f"Key file returned HTTP {response.status}; expected 200."
                )

            if "text/html" in response.headers.get(
                "Content-Type", ""
            ).lower():
                raise ValidationError(
                    "The key file URL returned HTML instead of plain text."
                )

            raw = response.read(1_048_577)
            if len(raw) > 1_048_576:
                raise ValidationError("The key file is unexpectedly large.")

            try:
                content = raw.decode("utf-8-sig").strip()
            except UnicodeDecodeError as exc:
                raise ValidationError(
                    "The key file is not valid UTF-8 text."
                ) from exc

    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            raise ValidationError(
                "The key file redirects. Enter its final URL directly."
            ) from exc
        raise ValidationError(
            f"Could not access the key file: HTTP {exc.code}."
        ) from exc
    except urllib.error.URLError as exc:
        raise ValidationError(
            f"Could not access the key file: {exc.reason}."
        ) from exc
    except TimeoutError as exc:
        raise ValidationError("Key file request timed out.") from exc
    except OSError as exc:
        raise ValidationError(f"Key file request failed: {exc}") from exc

    if content != key:
        raise ValidationError(
            "The key file content does not match the supplied key."
        )


def validate_url(value, host):
    value = value.strip()

    if not value or any(ch.isspace() for ch in value):
        raise ValidationError(
            f"URL is empty or contains whitespace: {value!r}"
        )

    if re.search(r"%(?![0-9A-Fa-f]{2})", value):
        raise ValidationError(f"Invalid percent-encoding: {value}")

    try:
        p = urlsplit(value)
        port = p.port
    except ValueError as exc:
        raise ValidationError(f"Invalid URL '{value}': {exc}") from exc

    if p.scheme.lower() not in ("http", "https"):
        raise ValidationError(f"URL must use HTTP or HTTPS: {value}")

    if not p.hostname or p.username or p.password:
        raise ValidationError(f"Invalid URL hostname or credentials: {value}")

    if port not in (None, 80, 443):
        raise ValidationError(f"Non-standard URL port: {value}")

    try:
        actual_host = p.hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValidationError(f"Invalid hostname in URL: {value}") from exc

    if actual_host != host:
        raise ValidationError(
            f"Host mismatch: {value} does not belong to {host}."
        )

    if p.fragment:
        raise ValidationError(
            f"Remove the fragment (#...) from this URL: {value}"
        )

    return value


def collect_urls(host):
    print("\nEnter URLs, one per line.")
    print("Type 'done' on a new line when finished.\n")

    urls = []
    seen = set()

    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break

        if line.lower() == "done":
            break

        if not line:
            continue

        # Allow multiple URLs pasted on one line, separated by whitespace.
        # URLs containing spaces should be percent-encoded.
        for value in line.split():
            if len(urls) >= MAX_URLS:
                raise ValidationError(
                    f"Maximum {MAX_URLS:,} URLs are allowed."
                )

            url = validate_url(value, host)

            if url not in seen:
                seen.add(url)
                urls.append(url)
            else:
                print(f"[INFO] Duplicate skipped: {url}")

    if not urls:
        raise ValidationError("No URLs were entered.")

    return urls


def check_key_scope(location, urls):
    path = urlsplit(location).path
    directory = path.rsplit("/", 1)[0] + "/"

    if directory == "/":
        return

    for url in urls:
        url_path = urlsplit(url).path
        if (
            url_path != directory.rstrip("/")
            and not url_path.startswith(directory)
        ):
            raise ValidationError(
                f"URL is outside the key file directory scope: {url}\n"
                f"Key file directory: {directory}"
            )


def submit(host, key, location, urls):
    payload = {
        "host": host,
        "key": key,
        "keyLocation": location,
        "urlList": urls,
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            status = response.status
            body = response.read(4096).decode(
                "utf-8", errors="replace"
            ).strip()
            headers = response.headers
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read(4096).decode(
            "utf-8", errors="replace"
        ).strip()
        headers = exc.headers
    except urllib.error.URLError as exc:
        print(f"[ERROR] Network request failed: {exc.reason}")
        return 1
    except TimeoutError:
        print("[ERROR] Submission request timed out.")
        return 1
    except OSError as exc:
        print(f"[ERROR] Submission failed: {exc}")
        return 1

    messages = {
        200: "URLs received successfully. Indexing is not guaranteed.",
        202: "Request accepted; key validation is pending.",
        400: "Bad request. Check the request format and URLs.",
        403: "Forbidden. The key may be invalid or unavailable.",
        422: "Unprocessable request. Check the host, URLs, and key.",
        429: "Too many requests. Wait before trying again.",
    }

    print(f"\n[INFO] HTTP status: {status}")
    print(messages.get(status, "Unexpected HTTP response."))

    if status == 429 and headers.get("Retry-After"):
        print(f"Retry-After: {headers.get('Retry-After')}")

    if body:
        print(f"Response: {body[:1000]}")

    return 0 if status in (200, 202) else 1


def main():
    global KEY

    print("=" * 48)
    print("       IndexNow URL Submission Tool")
    print("=" * 48)

    try:
        site_input = ask("\nWebsite URL: ")
        site, host = normalize_site(site_input)

        KEY = ask("IndexNow key: ")
        validate_key(KEY)

        print(f"\n[INFO] Website: {site}")
        print("[INFO] Checking DNS...")
        check_dns(host)
        print("[OK] DNS lookup passed.")

        location = get_key_location(site, host)
        print("[INFO] Verifying key file...")
        verify_key_file(location, KEY)
        print("[OK] Key file verified.")

        urls = collect_urls(host)
        check_key_scope(location, urls)

        print(f"\nWebsite: {site}")
        print(f"Unique URLs: {len(urls)}")

        print("\nURLs to submit:")
        for url in urls:
            print(f"  {url}")

        answer = ask("\nSubmit these URLs to IndexNow? [y/N]: ")
        if answer.lower() not in ("y", "yes"):
            print("[INFO] Submission cancelled.")
            return 0

        return submit(host, KEY, location, urls)

    except ValidationError as exc:
        print(f"\n[ERROR] {exc}")
        return 2
    except KeyboardInterrupt:
        print("\n[INFO] Cancelled by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
