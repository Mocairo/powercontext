"""Initial ticket query tool: listing and owner filtering only."""
import argparse
import json


TICKETS = [
    {"id": 4, "title": "Broken link", "owner": "bob", "status": "open"},
    {"id": 1, "title": "Login error", "owner": "alice", "status": "open"},
    {"id": 6, "title": "Update help", "owner": "carol", "status": "closed"},
    {"id": 3, "title": "Fix export", "owner": "alice", "status": "closed"},
    {"id": 5, "title": "Slow search", "owner": "alice", "status": "in_progress"},
    {"id": 2, "title": "Add metrics", "owner": "bob", "status": "in_progress"},
]


def list_tickets(owner=None):
    """Return tickets in ascending id order, optionally matching an exact owner."""
    return sorted(
        [dict(ticket) for ticket in TICKETS if owner is None or ticket["owner"] == owner],
        key=lambda ticket: ticket["id"],
    )


def main():
    parser = argparse.ArgumentParser(description="Query tickets")
    parser.add_argument("--owner", help="Filter by exact owner")
    args = parser.parse_args()
    print(json.dumps(list_tickets(owner=args.owner), ensure_ascii=False))


if __name__ == "__main__":
    main()
