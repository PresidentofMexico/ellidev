#!/usr/bin/env python3
"""
Salesforce Data Ingestion Tool

Syncs Salesforce data (opportunities, accounts, contacts) into the vector store
for semantic search and RAG.

Usage:
    python scripts/ingest_salesforce.py
    python scripts/ingest_salesforce.py --objects opportunities,accounts
    python scripts/ingest_salesforce.py --limit 50
    python scripts/ingest_salesforce.py --refresh
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path to import services
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.salesforce_rag import SalesforceRAG


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Ingest Salesforce data into vector store for RAG"
    )

    parser.add_argument(
        "--objects",
        type=str,
        default=None,
        help="Comma-separated list of objects to sync (opportunities,accounts,contacts). Default: all"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum records per object. Default: 100"
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Clear existing Salesforce data before ingesting (not yet implemented)"
    )

    return parser.parse_args()


def print_banner():
    """Print banner."""
    print("=" * 60)
    print("  Salesforce Data Ingestion Tool")
    print("  Sync CRM data into vector store for semantic search")
    print("=" * 60)
    print()


def print_stats(stats: dict):
    """
    Print ingestion statistics.

    Args:
        stats: Statistics dictionary from ingest_salesforce_data()
    """
    print("\n" + "=" * 60)
    print("  Ingestion Complete")
    print("=" * 60)
    print()
    print(f"📊 Opportunities: {stats['opportunities']}")
    print(f"🏢 Accounts:      {stats['accounts']}")
    print(f"👤 Contacts:      {stats['contacts']}")
    print(f"📦 Total Chunks:  {stats['total']}")

    if stats.get("errors"):
        print(f"\n⚠️  Errors: {len(stats['errors'])}")
        for error in stats["errors"][:5]:  # Show first 5 errors
            print(f"   • {error}")
        if len(stats["errors"]) > 5:
            print(f"   ... and {len(stats['errors']) - 5} more")

    print()


def main():
    """Main entry point."""
    args = parse_args()
    print_banner()

    # Parse objects list
    objects = None
    if args.objects:
        objects = [obj.strip() for obj in args.objects.split(",")]
        print(f"🎯 Target Objects: {', '.join(objects)}")
    else:
        print("🎯 Target Objects: All (opportunities, accounts, contacts)")

    # Show limit
    if args.limit:
        print(f"📏 Limit: {args.limit} records per object")
    else:
        print("📏 Limit: 100 records per object (default)")

    # Show refresh flag
    if args.refresh:
        print("🔄 Refresh Mode: ON (will clear existing data)")
    else:
        print("➕ Refresh Mode: OFF (incremental)")

    print()

    # Initialize Salesforce RAG service
    print("🔧 Initializing Salesforce RAG service...")
    sf_rag = SalesforceRAG()

    if not sf_rag.enabled:
        print("❌ Salesforce RAG is disabled in configuration")
        print("   Set SALESFORCE_RAG_ENABLED=true in .env to enable")
        sys.exit(1)

    # Override limit if specified
    if args.limit:
        sf_rag.limit = args.limit

    print()

    # Run ingestion
    try:
        stats = sf_rag.ingest_salesforce_data(
            objects=objects,
            refresh=args.refresh
        )

        # Print results
        print_stats(stats)

        # Exit code
        if stats.get("errors"):
            print("⚠️  Completed with errors")
            sys.exit(1)
        else:
            print("✅ Success!")
            sys.exit(0)

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
