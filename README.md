# IndexNow URL Submission Tool

A simple interactive Python command-line tool for submitting website
URLs to the [IndexNow API](https://www.indexnow.org/).

The script validates your website and URLs, checks that the IndexNow key
file is publicly accessible and contains the expected key, removes
duplicate URLs, and asks for confirmation before submitting the URL
list.

## Features

-   Interactive command-line prompts.
-   Accepts a website origin such as `https://example.com` (HTTPS
    required).
-   Checks DNS resolution before continuing.
-   Validates the IndexNow key format and verifies the key file's
    contents.
-   Supports the default key-file URL or a custom HTTPS key-file URL on
    the same hostname.
-   Accepts multiple URLs pasted on one line or entered one per line.
-   Skips duplicate URLs.
-   Checks that submitted URLs belong to the configured hostname.
-   Checks key-file directory scope when a key file is stored in a
    subdirectory.
-   Displays the URLs and requests confirmation before submission.
-   Handles common HTTP responses and network errors.

## Requirements

-   Python 3.9 or later is recommended.
-   An internet connection.
-   A website using HTTPS.
-   A valid IndexNow key and a publicly accessible key file.

The script uses only Python standard-library modules; no third-party
packages are required.

## Setup

1.  Save `bing.py` to a local folder.
2.  Create or obtain an IndexNow key according to the [IndexNow
    documentation](https://www.indexnow.org/documentation).
3.  Publish the key file on your website so it is publicly accessible
    over HTTPS and its plain-text contents exactly match your key.

By default, the script expects the key file at:

``` text
https://example.com/YOUR_INDEXNOW_KEY.txt
```

Replace `example.com` and `YOUR_INDEXNOW_KEY` with your actual domain
and key. During execution, you can enter a custom key-file URL instead.

## Run

Open a terminal or command prompt in the folder containing `bing.py`,
then run:

``` bash
python bing.py
```

On some systems, use:

``` bash
python3 bing.py
```

## How to use

1.  **Enter the website URL.** Enter a domain such as `example.com` or
    `https://example.com`. The website origin must use HTTPS; do not
    include a path, query string, or fragment.
2.  **Enter the IndexNow key.** The key must be 8--128 characters and
    contain only letters, numbers, or hyphens.
3.  **Choose the key-file URL.** Press Enter to use the default URL, or
    enter a custom HTTPS file URL on the same hostname.
4.  **Enter URLs to submit.** Type or paste URLs belonging to the
    configured hostname. Enter one per line, or paste multiple
    whitespace-separated URLs on a line.
5.  **Finish the list.** Type `done` on a new line.
6.  **Review and confirm.** Check the unique URL list and enter `y` or
    `yes` to submit. Any other response cancels submission.

Example URL input:

``` text
https://example.com/
https://example.com/about
https://example.com/products/item-1
done
```

## Validation and limits

-   Website origin: HTTPS only, default HTTPS port only, and a
    public-looking domain name.
-   URL schemes: HTTP and HTTPS are accepted for submitted URLs.
-   URL hostnames: must match the configured website hostname.
-   URL ports: only default HTTP/HTTPS ports (`80` and `443`) are
    accepted.
-   URL fragments (the `#...` portion) are rejected.
-   URLs containing whitespace are rejected; encode spaces in URLs.
-   Duplicate URL strings are skipped.
-   Maximum URL count: **10,000** per run.
-   Network timeout: **20 seconds** for requests.
-   A custom key file must use HTTPS, be on the same hostname, and
    return plain text matching the key. Redirects are not followed for
    key-file verification.
-   If the key file is in a subdirectory, submitted URLs must fall
    within that directory's scope.

## Understanding the response

The script reports the HTTP status returned by the IndexNow endpoint.
Common responses include:

  Status   Meaning shown by the tool
  -------- ---------------------------------------------------------
  `200`    URLs received successfully; indexing is not guaranteed.
  `202`    Request accepted; key validation is pending.
  `400`    Bad request; check the request format and URLs.
  `403`    The key may be invalid or unavailable.
  `422`    Check the host, URLs, and key.
  `429`    Too many requests; wait before retrying.

A successful response does **not** guarantee that a search engine will
crawl or index the submitted URLs.

## Troubleshooting

-   **DNS lookup failed:** Check the domain spelling, DNS records, and
    internet connection.
-   **Key file could not be accessed:** Confirm the file is published
    and returns HTTP `200` over HTTPS.
-   **Key mismatch:** Make sure the file contains exactly the key,
    without extra text.
-   **Key file redirects:** Enter the final key-file URL directly.
-   **Host mismatch:** Ensure every submitted URL uses the same hostname
    as the website entered at the start. A `www` hostname and a
    non-`www` hostname are treated as different hosts by this script.
-   **URL outside key-file directory scope:** Put the key file at the
    website root or submit only URLs within the key file's directory
    scope.
-   **HTTP `429`:** Wait before trying again and respect any
    `Retry-After` value displayed by the server.

## Security and usage notes

-   Do not share your IndexNow key unnecessarily.
-   The script sends the key, key-file location, hostname, and URL list
    to the IndexNow API.
-   Review the URL list before confirming submission.
-   URL submission is a notification to IndexNow; it does not guarantee
    indexing or ranking improvements.

## License

No license is specified in this repository. Add a license file if you
intend to distribute the project and want to define reuse terms.
