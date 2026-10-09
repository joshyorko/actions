# Changelog
## Unreleased — 1.0.3 candidate

- Honor the selected network profile’s explicit no-proxy destinations for
  urllib3 requests, while retaining proxy routing for other destinations and
  the identical configured TLS verification context.
- Route proxy-to-direct redirects with the destination Host value unless the
  caller supplied Host explicitly; preserve repeated HTTP header fields while
  filtering generated Host values.



## 1.0.1 - 2026-09-07

- Correct distribution author and maintainer metadata to Joshua Yorko.

## Unreleased

- Migration: move `network-settings.yaml` from `~/.sema4ai` to
  `~/.actions` (or `%LOCALAPPDATA%/actions` on Windows). There is no legacy
  fallback; the persisted proxy key is `no-proxy`.

## 2.1.2 - 2025-12-17

- CVE fix (urllib3 >= 2.6.2)

## 2.1.1 - 2025-08-21

- CVE fix (urllib3 >= 2.5.0)

## 2.1.0 - 2025-04-28

- Add `get_network_profile()` method to `actions-http-helper`
- Started tracking releases
