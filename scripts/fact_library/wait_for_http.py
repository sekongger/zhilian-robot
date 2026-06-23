from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait until an HTTP endpoint becomes reachable.")
    parser.add_argument("--url", required=True, help="HTTP URL to probe.")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds.")
    parser.add_argument("--interval", type=float, default=5.0, help="Retry interval in seconds.")
    args = parser.parse_args()

    deadline = time.time() + args.timeout
    last_error = ""
    while time.time() < deadline:
        try:
            req = urllib.request.Request(args.url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(
                    json.dumps(
                        {
                            "url": args.url,
                            "status": resp.status,
                            "reachable": True,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return 0
        except urllib.error.HTTPError as exc:
            print(
                json.dumps(
                    {
                        "url": args.url,
                        "status": exc.code,
                        "reachable": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            time.sleep(args.interval)

    print(
        json.dumps(
            {
                "url": args.url,
                "reachable": False,
                "error": last_error,
            },
            ensure_ascii=False,
            indent=2,
        ),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
