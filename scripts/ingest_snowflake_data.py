#!/usr/bin/env python3
"""
Snowflake Security Master Data Ingestion Tool

Pulls financial data from Snowflake security master tables and ingests
it into the vector store for semantic search and RAG.

Usage:
    python scripts/ingest_snowflake_data.py
    python scripts/ingest_snowflake_data.py --limit 500
    python scripts/ingest_snowflake_data.py --refresh
"""

import argparse
import sys
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path to import services
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.vector_store import VectorStore
from services.logger import logger


# SQL query to fetch security master data
SECURITY_MASTER_QUERY = """
SELECT
    a.ISSUER_ID, a.ISSUER_LONG_NAME, a.ISSUER_TICKER, a.ISSUER_COUNTRY,
    a.GICS_SECTOR_DESC_LVL_1, a.GICS_SECTOR_DESC_LVL_3,
    a.MOODYS_LONG_RATING, a.SNP_LONG_RATING,
    b.CUSIP, b.ISIN, b.ASSET_CLASS_STRAT, b.SM_SEC_TYPE,
    b.DESC_INSTMT, b.MATURITY, b.COUPON, b.CURRENCY
FROM blackrock_eldmuse2sf_aladdindb_share.investments.issuers a
JOIN blackrock_eldmuse2sf_aladdindb_share.investments.security_master b
  ON a.issuer_id = b.issuer_id
LIMIT {limit}
"""


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Ingest Snowflake security master data into vector store for RAG"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum records to fetch. Default: 1000"
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Clear existing Aladdin data before ingesting"
    )

    return parser.parse_args()


def print_banner():
    """Print banner."""
    print("=" * 60)
    print("  Snowflake Security Master Data Ingestion Tool")
    print("  Sync Aladdin data into vector store for semantic search")
    print("=" * 60)
    print()


def format_value(value, default: str = "N/A") -> str:
    """
    Format a value for display, handling None/NULL gracefully.

    Args:
        value: The value to format
        default: Default string if value is None

    Returns:
        Formatted string
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return default
    return str(value)


def format_row_as_chunk(row: Dict) -> str:
    """
    Format a security master row into a readable text chunk.

    Args:
        row: Dictionary containing security master data

    Returns:
        Formatted text block for the chunk
    """
    lines = []

    # Security header
    issuer_name = format_value(row.get("ISSUER_LONG_NAME"), "Unknown Issuer")
    ticker = format_value(row.get("ISSUER_TICKER"), "")
    if ticker and ticker != "N/A":
        lines.append(f"Security: {issuer_name} ({ticker})")
    else:
        lines.append(f"Security: {issuer_name}")

    # Type information
    asset_class = format_value(row.get("ASSET_CLASS_STRAT"), "")
    sec_type = format_value(row.get("SM_SEC_TYPE"), "")
    if asset_class != "N/A" or sec_type != "N/A":
        type_parts = [p for p in [asset_class, sec_type] if p != "N/A"]
        if type_parts:
            lines.append(f"Type: {' - '.join(type_parts)}")

    # Sector information
    sector_l1 = format_value(row.get("GICS_SECTOR_DESC_LVL_1"), "")
    sector_l3 = format_value(row.get("GICS_SECTOR_DESC_LVL_3"), "")
    if sector_l1 != "N/A" or sector_l3 != "N/A":
        sector_parts = [p for p in [sector_l1, sector_l3] if p != "N/A"]
        if sector_parts:
            lines.append(f"Sector: {' / '.join(sector_parts)}")

    # Country
    country = format_value(row.get("ISSUER_COUNTRY"), "")
    if country != "N/A":
        lines.append(f"Country: {country}")

    # Ratings
    moodys = format_value(row.get("MOODYS_LONG_RATING"), "")
    snp = format_value(row.get("SNP_LONG_RATING"), "")
    if moodys != "N/A" or snp != "N/A":
        rating_parts = []
        if moodys != "N/A":
            rating_parts.append(f"Moody's: {moodys}")
        if snp != "N/A":
            rating_parts.append(f"S&P: {snp}")
        lines.append(f"Ratings: {', '.join(rating_parts)}")

    # Details (instrument description, maturity, coupon)
    desc = format_value(row.get("DESC_INSTMT"), "")
    maturity = format_value(row.get("MATURITY"), "")
    coupon = row.get("COUPON")
    currency = format_value(row.get("CURRENCY"), "")

    if desc != "N/A":
        detail_parts = [desc]
        if maturity != "N/A":
            detail_parts.append(f"Mat: {maturity}")
        if coupon is not None:
            detail_parts.append(f"Cpn: {coupon}%")
        if currency != "N/A":
            detail_parts.append(f"Ccy: {currency}")
        lines.append(f"Details: {' | '.join(detail_parts)}")

    # Identifiers
    cusip = format_value(row.get("CUSIP"), "")
    isin = format_value(row.get("ISIN"), "")
    if cusip != "N/A" or isin != "N/A":
        id_parts = []
        if cusip != "N/A":
            id_parts.append(f"CUSIP: {cusip}")
        if isin != "N/A":
            id_parts.append(f"ISIN: {isin}")
        lines.append(f"IDs: {', '.join(id_parts)}")

    return "\n".join(lines)


def create_chunk_metadata(row: Dict) -> Dict:
    """
    Create metadata dictionary for a security chunk.

    Args:
        row: Dictionary containing security master data

    Returns:
        Metadata dictionary
    """
    return {
        "source": "aladdin_security_master",
        "type": "security_master_record",
        "issuer_id": row.get("ISSUER_ID"),
        "cusip": row.get("CUSIP"),
        "isin": row.get("ISIN"),
        "ticker": row.get("ISSUER_TICKER"),
        "issuer_name": row.get("ISSUER_LONG_NAME"),
        "asset_class": row.get("ASSET_CLASS_STRAT"),
        "sec_type": row.get("SM_SEC_TYPE"),
        "sector": row.get("GICS_SECTOR_DESC_LVL_1"),
        "country": row.get("ISSUER_COUNTRY"),
        "moodys_rating": row.get("MOODYS_LONG_RATING"),
        "snp_rating": row.get("SNP_LONG_RATING"),
        "currency": row.get("CURRENCY"),
    }


def generate_chunk_id(row: Dict) -> str:
    """
    Generate a unique chunk ID for a security record.

    Args:
        row: Dictionary containing security master data

    Returns:
        Unique chunk ID string
    """
    # Use CUSIP or ISIN as primary identifier, fall back to UUID
    cusip = row.get("CUSIP")
    isin = row.get("ISIN")
    issuer_id = row.get("ISSUER_ID")

    if cusip:
        return f"aladdin_sec_{cusip}"
    elif isin:
        return f"aladdin_sec_{isin}"
    elif issuer_id:
        return f"aladdin_issuer_{issuer_id}_{uuid.uuid4().hex[:8]}"
    else:
        return f"aladdin_sec_{uuid.uuid4().hex}"


def connect_to_snowflake():
    """
    Connect to Snowflake using environment variables.

    Returns:
        Snowflake connection object or None if connection fails
    """
    # Check required env vars
    user = os.environ.get("SNOWFLAKE_USER")
    account = os.environ.get("SNOWFLAKE_ACCOUNT")
    warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE")

    if not all([user, account, warehouse]):
        logger.error(
            "Missing Snowflake credentials. Required: SNOWFLAKE_USER, SNOWFLAKE_ACCOUNT, SNOWFLAKE_WAREHOUSE",
            service="ingest_snowflake"
        )
        return None

    try:
        import snowflake.connector

        # Check for key-pair auth first
        private_key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")

        if private_key_path:
            # Key-pair authentication
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization

            with open(private_key_path, "rb") as key_file:
                passphrase = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
                p_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=passphrase.encode() if passphrase else None,
                    backend=default_backend()
                )

            pkb = p_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            connection = snowflake.connector.connect(
                user=user,
                account=account,
                warehouse=warehouse,
                database=os.environ.get("SNOWFLAKE_DATABASE"),
                schema=os.environ.get("SNOWFLAKE_SCHEMA"),
                role=os.environ.get("SNOWFLAKE_ROLE"),
                private_key=pkb,
            )
            logger.info(
                "Connected to Snowflake via key-pair authentication",
                service="ingest_snowflake",
                auth_method="key_pair"
            )
        else:
            # Password authentication (fallback)
            password = os.environ.get("SNOWFLAKE_PASSWORD")
            if not password:
                logger.error(
                    "No SNOWFLAKE_PASSWORD or SNOWFLAKE_PRIVATE_KEY_PATH provided",
                    service="ingest_snowflake"
                )
                return None

            connection = snowflake.connector.connect(
                user=user,
                password=password,
                account=account,
                warehouse=warehouse,
                database=os.environ.get("SNOWFLAKE_DATABASE"),
                schema=os.environ.get("SNOWFLAKE_SCHEMA"),
                role=os.environ.get("SNOWFLAKE_ROLE"),
            )
            logger.info(
                "Connected to Snowflake via password authentication",
                service="ingest_snowflake",
                auth_method="password"
            )

        return connection

    except ImportError:
        logger.error(
            "snowflake-connector-python not installed. Run: pip install snowflake-connector-python",
            service="ingest_snowflake"
        )
        return None
    except Exception as e:
        logger.error(
            f"Could not connect to Snowflake: {e}",
            service="ingest_snowflake",
            error=str(e)
        )
        return None


def fetch_security_data(connection, limit: int) -> List[Dict]:
    """
    Fetch security master data from Snowflake.

    Args:
        connection: Snowflake connection
        limit: Maximum number of records to fetch

    Returns:
        List of row dictionaries
    """
    try:
        cursor = connection.cursor()

        query = SECURITY_MASTER_QUERY.format(limit=limit)
        logger.info(
            f"Executing security master query (limit: {limit})",
            service="ingest_snowflake"
        )

        cursor.execute(query)

        # Get column names
        columns = [desc[0] for desc in cursor.description]

        # Fetch all rows as dictionaries
        rows = []
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            rows.append(row_dict)

        cursor.close()

        logger.info(
            f"Fetched {len(rows)} security records from Snowflake",
            service="ingest_snowflake",
            record_count=len(rows)
        )

        return rows

    except Exception as e:
        logger.error(
            f"Error fetching security data: {e}",
            service="ingest_snowflake",
            error=str(e)
        )
        return []


def delete_existing_aladdin_data(vector_store: VectorStore) -> int:
    """
    Delete existing Aladdin data from vector store.

    Args:
        vector_store: VectorStore instance

    Returns:
        Number of chunks deleted
    """
    if vector_store.is_mock:
        # For mock mode, filter out aladdin chunks
        original_count = len(vector_store.mock_chunks)
        vector_store.mock_chunks = [
            c for c in vector_store.mock_chunks
            if c.get("metadata", {}).get("source") != "aladdin_security_master"
        ]
        deleted = original_count - len(vector_store.mock_chunks)
        logger.info(
            f"Deleted {deleted} existing Aladdin chunks from mock store",
            service="ingest_snowflake",
            deleted_count=deleted
        )
        return deleted
    else:
        # For real Snowflake, we'd need to delete by source
        # This would require a custom query based on metadata
        logger.warning(
            "Refresh for Snowflake vector store not fully implemented",
            service="ingest_snowflake"
        )
        return 0


def ingest_security_data(
    rows: List[Dict],
    vector_store: VectorStore
) -> Dict:
    """
    Convert security records to chunks and ingest into vector store.

    Args:
        rows: List of security record dictionaries
        vector_store: VectorStore instance

    Returns:
        Statistics dictionary
    """
    stats = {
        "total_records": len(rows),
        "chunks_created": 0,
        "chunks_ingested": 0,
        "errors": []
    }

    if not rows:
        return stats

    chunks = []

    for row in rows:
        try:
            # Format the row as a readable chunk
            content = format_row_as_chunk(row)

            # Create metadata
            metadata = create_chunk_metadata(row)

            # Generate unique chunk ID
            chunk_id = generate_chunk_id(row)

            # Create document ID (group by issuer)
            issuer_id = row.get("ISSUER_ID", "unknown")
            document_id = f"aladdin_issuer_{issuer_id}"

            chunk = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "content": content,
                "metadata": metadata,
            }

            chunks.append(chunk)
            stats["chunks_created"] += 1

        except Exception as e:
            error_msg = f"Error processing row {row.get('CUSIP', 'unknown')}: {e}"
            stats["errors"].append(error_msg)
            logger.error(error_msg, service="ingest_snowflake")

    # Ingest chunks in batches
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        try:
            success = vector_store.ingest_documents(batch)
            if success:
                stats["chunks_ingested"] += len(batch)
                logger.info(
                    f"Ingested batch {i // batch_size + 1} ({len(batch)} chunks)",
                    service="ingest_snowflake",
                    batch_num=i // batch_size + 1,
                    batch_size=len(batch)
                )
            else:
                error_msg = f"Failed to ingest batch {i // batch_size + 1}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, service="ingest_snowflake")
        except Exception as e:
            error_msg = f"Error ingesting batch {i // batch_size + 1}: {e}"
            stats["errors"].append(error_msg)
            logger.error(error_msg, service="ingest_snowflake")

    return stats


def print_stats(stats: Dict):
    """
    Print ingestion statistics.

    Args:
        stats: Statistics dictionary from ingest_security_data()
    """
    print("\n" + "=" * 60)
    print("  Ingestion Complete")
    print("=" * 60)
    print()
    print(f"Total Records Fetched:  {stats['total_records']}")
    print(f"Chunks Created:         {stats['chunks_created']}")
    print(f"Chunks Ingested:        {stats['chunks_ingested']}")

    if stats.get("errors"):
        print(f"\nErrors: {len(stats['errors'])}")
        for error in stats["errors"][:5]:
            print(f"   - {error}")
        if len(stats["errors"]) > 5:
            print(f"   ... and {len(stats['errors']) - 5} more")

    print()


def main():
    """Main entry point."""
    args = parse_args()
    print_banner()

    # Show configuration
    print(f"Record Limit: {args.limit}")
    if args.refresh:
        print("Refresh Mode: ON (will clear existing Aladdin data)")
    else:
        print("Refresh Mode: OFF (incremental)")
    print()

    # Connect to Snowflake
    print("Connecting to Snowflake...")
    connection = connect_to_snowflake()

    if not connection:
        print("Could not connect to Snowflake. Check your credentials in .env")
        print("Required: SNOWFLAKE_USER, SNOWFLAKE_ACCOUNT, SNOWFLAKE_WAREHOUSE")
        print("Auth: SNOWFLAKE_PASSWORD or SNOWFLAKE_PRIVATE_KEY_PATH")
        sys.exit(1)

    print("Connected to Snowflake")
    print()

    # Initialize vector store
    print("Initializing vector store...")
    vector_store = VectorStore()

    # Handle refresh
    if args.refresh:
        print("Clearing existing Aladdin data...")
        deleted = delete_existing_aladdin_data(vector_store)
        print(f"Deleted {deleted} existing chunks")
        print()

    # Fetch data
    print(f"Fetching security master data (limit: {args.limit})...")
    rows = fetch_security_data(connection, args.limit)

    if not rows:
        print("No data fetched. Check query and permissions.")
        connection.close()
        sys.exit(1)

    print(f"Fetched {len(rows)} records")
    print()

    # Preview first record
    if rows:
        print("Sample formatted chunk:")
        print("-" * 40)
        print(format_row_as_chunk(rows[0]))
        print("-" * 40)
        print()

    # Ingest data
    print("Ingesting data into vector store...")
    stats = ingest_security_data(rows, vector_store)

    # Clean up
    connection.close()
    vector_store.close()

    # Print results
    print_stats(stats)

    # Exit code
    if stats.get("errors"):
        print("Completed with errors")
        sys.exit(1)
    else:
        print("Success!")
        sys.exit(0)


if __name__ == "__main__":
    main()
