"""Ticket query tool with owner and status filtering."""
import argparse
import json


VALID_STATUSES = ("open", "in_progress", "closed")

TICKETS = [
    {"id": 4, "title": "Broken link", "owner": "bob", "status": "open"},
    {"id": 1, "title": "Login error", "owner": "alice", "status": "open"},
    {"id": 6, "title": "Update help", "owner": "carol", "status": "closed"},
    {"id": 3, "title": "Fix export", "owner": "alice", "status": "closed"},
    {"id": 5, "title": "Slow search", "owner": "alice", "status": "in_progress"},
    {"id": 2, "title": "Add metrics", "owner": "bob", "status": "in_progress"},
]


def list_tickets(owner=None, status=None):
    """Return tickets in ascending id order, filtered by owner and status."""
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(
            "invalid status {!r}; expected one of: {}".format(
                status, ", ".join(VALID_STATUSES)
            )
        )

    return sorted(
        [
            dict(ticket)
            for ticket in TICKETS
            if (owner is None or ticket["owner"] == owner)
            and (status is None or ticket["status"] == status)
        ],
        key=lambda ticket: ticket["id"],
    )


def _status_argument(value):
    if value not in VALID_STATUSES:
        raise argparse.ArgumentTypeError(
            "invalid status {!r}; expected one of: {}".format(
                value, ", ".join(VALID_STATUSES)
            )
        )
    return value


def main():
    parser = argparse.ArgumentParser(description="Query tickets")
    parser.add_argument("--owner", help="Filter by exact owner")
    parser.add_argument(
        "--status",
        type=_status_argument,
        help="Filter by status (open, in_progress, closed)",
    )
    args = parser.parse_args()
    print(json.dumps(list_tickets(owner=args.owner, status=args.status), ensure_ascii=False))


if __name__ == "__main__":
    main()
