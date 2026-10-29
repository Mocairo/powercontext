"""Initial ticket query tool: listing and owner/status filtering only."""
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
    """Return tickets in ascending id order, optionally matching exact owner and status."""
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(
            "invalid status {!r}; valid statuses are: {}".format(
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


def main():
    parser = argparse.ArgumentParser(description="Query tickets")
    parser.add_argument("--owner", help="Filter by exact owner")
    parser.add_argument("--status", help="Filter by exact status")
    args = parser.parse_args()
    try:
        tickets = list_tickets(owner=args.owner, status=args.status)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(tickets, ensure_ascii=False))


if __name__ == "__main__":
    main()
