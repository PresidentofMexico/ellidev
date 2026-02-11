"""
Deal Message Parser for extracting opportunity details from Slack messages.

Parses structured deal messages and extracts fields to pre-fill Salesforce
opportunity creation modals.
"""

import re
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from services.logger import logger


@dataclass
class ParsedDeal:
    """Represents a parsed deal from a Slack message."""
    # Required Salesforce fields
    opportunity_name: Optional[str] = None
    strategy: Optional[str] = None
    security_type: Optional[str] = None
    stage: Optional[str] = None
    close_date: Optional[str] = None

    # Optional fields
    amount: Optional[int] = None
    company_name: Optional[str] = None
    source: Optional[str] = None
    sponsor: Optional[str] = None
    transaction_type: Optional[str] = None

    # Additional context
    overview: Optional[str] = None
    recommendation: Optional[str] = None

    # Raw message for reference
    raw_message: str = ""

    # Parsing confidence (0-1)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/debugging."""
        return {
            "opportunity_name": self.opportunity_name,
            "strategy": self.strategy,
            "security_type": self.security_type,
            "stage": self.stage,
            "close_date": self.close_date,
            "amount": self.amount,
            "company_name": self.company_name,
            "source": self.source,
            "sponsor": self.sponsor,
            "transaction_type": self.transaction_type,
            "confidence": self.confidence,
        }


# Strategy mapping from common terms to Salesforce picklist values
STRATEGY_MAPPING = {
    "private credit": "Corporate Credit",
    "diversified credit": "Corporate Credit",
    "corporate credit": "Corporate Credit",
    "direct lending": "Corporate Credit",
    "senior lending": "Corporate Credit",
    "mezzanine": "Corporate Credit",
    "mezz": "Corporate Credit",
    "re credit": "RE Credit",
    "real estate credit": "RE Credit",
    "real estate debt": "RE Credit",
    "re equity": "RE Equity",
    "real estate equity": "RE Equity",
    "structured credit": "Structured Credit",
    "clo": "Structured Credit",
    "abs": "Structured Credit",
    "asset based": "Asset Based",
    "abl": "Asset Based",
    "gp solutions": "GP Solutions",
    "gp stakes": "GP Solutions",
    "eldridge industries": "Eldridge Industries",
    "sports": "Eldridge Sports & Entertainment",
    "entertainment": "Eldridge Sports & Entertainment",
    "media": "Eldridge Sports & Entertainment",
}

# Security type mapping from common terms
SECURITY_TYPE_MAPPING = {
    "term loan": "Term Loan",
    "tl": "Term Loan",
    "first lien": "1L Term Loan A",
    "1l": "1L Term Loan A",
    "second lien": "2L Term Loan",
    "2l": "2L Term Loan",
    "ddtl": "Delay Draw Term Loan",
    "delayed draw": "Delay Draw Term Loan",
    "revolver": "Revolving Line of Credit",
    "rloc": "Revolving Line of Credit",
    "revolving": "Revolving Line of Credit",
    "bond": "Bond",
    "notes": "Bond",
    "senior notes": "Bond",
    "equity": "Common Equity",
    "common equity": "Common Equity",
    "preferred": "Preferred Equity",
    "preferred equity": "Preferred Equity",
    "mezzanine": "Junior Sub Debt",
    "mezz": "Junior Sub Debt",
    "subordinated": "Subordinated Debt",
    "sub debt": "Subordinated Debt",
    "junior": "Junior Sub Debt",
    "junior secured": "Junior Sub Debt",
    "clo": "CLO",
    "fund": "Fund Commitment",
    "fund commitment": "Fund Commitment",
    "gp stake": "GP Stakes",
    "gp interest": "GP Interest",
}

# Stage mapping from common terms
STAGE_MAPPING = {
    "initial": "Initial Review",
    "initial review": "Initial Review",
    "initial interest": "Initial Review",
    "proposal": "Proposal",
    "term sheet": "Term Sheet",
    "ts": "Term Sheet",
    "diligence": "Diligence",
    "dd": "Diligence",
    "due diligence": "Diligence",
    "execution": "Execution",
    "closing": "Pre-Close",
    "pre-close": "Pre-Close",
    "tracking": "Tracking",
    "pass": "Passed",
    "passed": "Passed",
    "dead": "Dead",
}


def parse_deal_message(message: str) -> ParsedDeal:
    """
    Parse a Slack message to extract deal information.

    Args:
        message: Raw Slack message text

    Returns:
        ParsedDeal object with extracted fields
    """
    parsed = ParsedDeal(raw_message=message)
    fields_found = 0
    total_fields = 5  # Number of required fields we're looking for

    # Clean up the message (remove Slack formatting)
    clean_message = _clean_slack_message(message)

    # Extract Opportunity Name
    parsed.opportunity_name = _extract_opportunity_name(clean_message)
    if parsed.opportunity_name:
        fields_found += 1

    # Extract Strategy
    parsed.strategy = _extract_strategy(clean_message)
    if parsed.strategy:
        fields_found += 1

    # Extract Security Type
    parsed.security_type = _extract_security_type(clean_message)
    if parsed.security_type:
        fields_found += 1

    # Extract Stage
    parsed.stage = _extract_stage(clean_message)
    if parsed.stage:
        fields_found += 1

    # Extract Close Date
    parsed.close_date = _extract_close_date(clean_message)
    if parsed.close_date:
        fields_found += 1

    # Extract Amount
    parsed.amount = _extract_amount(clean_message)

    # Extract additional context
    parsed.company_name = _extract_company_name(clean_message)
    parsed.source = _extract_deal_source(clean_message)
    parsed.sponsor = _extract_sponsor(clean_message)
    parsed.transaction_type = _extract_field(clean_message, r"Transaction Type:\s*(.+?)(?:\n|$)")
    parsed.overview = _extract_field(clean_message, r"Transaction Overview:\s*(.+?)(?:Recommendation:|Company Overview:|$)", flags=re.DOTALL)
    parsed.recommendation = _extract_field(clean_message, r"Recommendation:\s*(.+?)(?:Company Overview:|Financial|$)", flags=re.DOTALL)

    # Calculate confidence score
    parsed.confidence = fields_found / total_fields

    logger.info(
        "Parsed deal message",
        service="deal_parser",
        opportunity_name=parsed.opportunity_name,
        strategy=parsed.strategy,
        security_type=parsed.security_type,
        stage=parsed.stage,
        confidence=parsed.confidence,
        fields_found=fields_found,
    )

    return parsed


def _clean_slack_message(message: str) -> str:
    """Remove Slack formatting from message."""
    # Remove user mentions like <@U12345678>
    clean = re.sub(r'<@[A-Z0-9]+>', '', message)
    # Remove channel mentions like <#C12345678|channel-name>
    clean = re.sub(r'<#[A-Z0-9]+\|[^>]+>', '', clean)
    # Remove URLs
    clean = re.sub(r'<https?://[^>]+>', '', clean)
    # Remove bold/italic markers
    clean = clean.replace('*', '').replace('_', '')
    # Normalize whitespace
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def _extract_opportunity_name(message: str) -> Optional[str]:
    """Extract opportunity/company name from message."""
    # Try explicit Opportunity: field first
    match = re.search(r'Opportunity:\s*(.+?)(?:\n|Strategy:|Source:|$)', message, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        # Clean up any trailing field indicators
        name = re.sub(r'\s*(Strategy|Source|Originator):.*$', '', name, flags=re.IGNORECASE)
        return name[:120]  # Salesforce limit

    # Try to find company name from first line or Company: field
    match = re.search(r'Company(?:\s+Name)?:\s*(.+?)(?:\n|$)', message, re.IGNORECASE)
    if match:
        return match.group(1).strip()[:120]

    return None


def _extract_company_name(message: str) -> Optional[str]:
    """Extract company name separately from opportunity name."""
    # Look in Company Overview section
    match = re.search(r'Company Overview:\s*([^,]+)', message, re.IGNORECASE)
    if match:
        # Extract first company name mentioned
        name = match.group(1).strip()
        # Remove common prefixes
        name = re.sub(r'^(The\s+)?', '', name)
        # Take first part before common words
        name = re.split(r'\s+(is|was|founded|headquartered|operates)', name, flags=re.IGNORECASE)[0]
        return name.strip()

    return None


def _extract_strategy(message: str) -> Optional[str]:
    """Extract and map strategy from message."""
    # Look for explicit Strategy: field
    match = re.search(r'Strategy:\s*(.+?)(?:\n|Source:|$)', message, re.IGNORECASE)
    if match:
        strategy_text = match.group(1).strip().lower()

        # Try to map to known strategy
        for key, value in STRATEGY_MAPPING.items():
            if key in strategy_text:
                return value

        # Check for direct matches with picklist values
        strategy_text_clean = match.group(1).strip()
        from services.sf_client import STRATEGY_VALUES
        for strategy in STRATEGY_VALUES:
            if strategy.lower() in strategy_text.lower():
                return strategy

    # Fallback: scan entire message for strategy keywords
    message_lower = message.lower()
    for key, value in STRATEGY_MAPPING.items():
        if key in message_lower:
            return value

    return None


def _extract_security_type(message: str) -> Optional[str]:
    """Extract and map security type from message."""
    message_lower = message.lower()

    # Look for specific security type mentions in transaction overview
    # Order matters - check more specific terms first
    security_checks = [
        ("delayed draw term loan", "Delay Draw Term Loan"),
        ("ddtl", "Delay Draw Term Loan"),
        ("junior secured", "Junior Sub Debt"),
        ("junior term loan", "Junior Sub Debt"),
        ("first lien term loan", "1L Term Loan A"),
        ("1l term loan", "1L Term Loan A"),
        ("second lien", "2L Term Loan"),
        ("2l term loan", "2L Term Loan"),
        ("term loan", "Term Loan"),
        ("revolving line", "Revolving Line of Credit"),
        ("revolver", "Revolving Line of Credit"),
        ("mezzanine", "Junior Sub Debt"),
        ("subordinated", "Subordinated Debt"),
        ("preferred equity", "Preferred Equity"),
        ("common equity", "Common Equity"),
        ("equity", "Common Equity"),
        ("bond", "Bond"),
        ("notes", "Bond"),
    ]

    for keyword, security_type in security_checks:
        if keyword in message_lower:
            return security_type

    return None


def _extract_stage(message: str) -> Optional[str]:
    """Extract and map stage from message."""
    # Look for explicit Stage: field
    match = re.search(r'Stage:\s*(.+?)(?:\n|Transaction|$)', message, re.IGNORECASE)
    if match:
        stage_text = match.group(1).strip().lower()

        # Try to map to known stage
        for key, value in STAGE_MAPPING.items():
            if key in stage_text:
                return value

    # Check recommendation for pass/dead indicators
    if re.search(r'recommend(?:s|ation)?[:\s]+pass', message, re.IGNORECASE):
        return "Passed"

    # Default to Initial Review for new deals
    return "Initial Review"


def _extract_close_date(message: str) -> Optional[str]:
    """Extract close date from message."""
    # Look for explicit date mentions
    patterns = [
        r'closing date[:\s]+(?:of\s+)?([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'target closing[:\s]+(?:date\s+)?(?:of\s+)?([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'close[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'closing[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'(?:target|expected).*?(\d{1,2}/\d{1,2}/\d{2,4})',
        r'([A-Za-z]+\s+\d{1,2},?\s+\d{4}).*?clos',
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            parsed_date = _parse_date(date_str)
            if parsed_date:
                return parsed_date

    # If no date found, default to end of current quarter
    return _default_close_date()


def _parse_date(date_str: str) -> Optional[str]:
    """Parse various date formats to YYYY-MM-DD."""
    date_formats = [
        "%B %d, %Y",      # February 10, 2026
        "%B %d %Y",       # February 10 2026
        "%b %d, %Y",      # Feb 10, 2026
        "%b %d %Y",       # Feb 10 2026
        "%m/%d/%Y",       # 02/10/2026
        "%m/%d/%y",       # 02/10/26
    ]

    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def _default_close_date() -> str:
    """Return end of current quarter as default close date."""
    today = datetime.now()
    quarter = (today.month - 1) // 3 + 1
    if quarter == 4:
        quarter_end = datetime(today.year, 12, 31)
    else:
        quarter_end_month = quarter * 3
        # Get last day of quarter
        if quarter_end_month == 3:
            quarter_end = datetime(today.year, 3, 31)
        elif quarter_end_month == 6:
            quarter_end = datetime(today.year, 6, 30)
        elif quarter_end_month == 9:
            quarter_end = datetime(today.year, 9, 30)
        else:
            quarter_end = datetime(today.year, 12, 31)

    return quarter_end.strftime("%Y-%m-%d")


def _extract_amount(message: str) -> Optional[int]:
    """Extract deal amount from message."""
    # Look for dollar amounts
    patterns = [
        r'\$(\d+)[\s-]*(?:to|-|–)[\s-]*\$?(\d+)\s*(?:million|mm|m\b)',  # $35-50 million
        r'\$(\d+(?:\.\d+)?)\s*(?:million|mm|m\b)',  # $50 million
        r'(\d+(?:\.\d+)?)\s*(?:million|mm|m\b).*?(?:financing|loan|deal)',  # 50 million financing
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            if match.lastindex == 2:
                # Range - take the higher number
                amount = float(match.group(2))
            else:
                amount = float(match.group(1))

            # Convert to actual amount (millions)
            return int(amount * 1_000_000)

    return None


def _extract_field(message: str, pattern: str, flags: int = 0) -> Optional[str]:
    """Generic field extraction using regex pattern."""
    match = re.search(pattern, message, re.IGNORECASE | flags)
    if match:
        value = match.group(1).strip()
        # Clean up and truncate
        value = re.sub(r'\s+', ' ', value)
        return value[:500] if len(value) > 500 else value
    return None


def _extract_sponsor(message: str) -> Optional[str]:
    """
    Extract primary sponsor name from message.

    Looks for various patterns including:
    - Sponsor: <name>
    - Primary Sponsor: <name>
    - PE Sponsor: <name>
    - backed by <name>
    - <name>-backed
    """
    # Try explicit sponsor field patterns
    # Use word-based patterns to avoid matching too much text
    patterns = [
        # Match "Sponsor: Name" - capture up to 5 words or until common delimiters
        r'(?:Primary\s+)?Sponsor:\s*([A-Za-z0-9][\w\s&\'-]{0,50}?)(?:\s+(?:Stage|Team|Source|Transaction|Originator|Deal|Initial|Term|is|has|and|with|,|\()|$)',
        r'PE\s+Sponsor:\s*([A-Za-z0-9][\w\s&\'-]{0,50}?)(?:\s+(?:Stage|Team|Source|Transaction|Originator|Deal|Initial|Term|is|has|,|\()|$)',
        # Match "backed by Name" patterns
        r'backed\s+by\s+([A-Z][A-Za-z\s&\'-]{2,40}?)(?:\s+(?:is|has|and|with|,|\.|\())',
        r'([A-Z][A-Za-z\s&\'-]{2,30}?)-backed',
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            sponsor = match.group(1).strip()
            # Clean up common suffixes and trailing punctuation
            sponsor = re.sub(r'\s*(LLC|LP|Inc|Corp|Capital|Partners|Management|Investors?)\.?$', '', sponsor, flags=re.IGNORECASE)
            sponsor = sponsor.rstrip(' ,.:;')
            # Validate: should be reasonable length and not contain field names
            if sponsor and 2 < len(sponsor) <= 60 and not re.search(r'Stage|Source|Team|Transaction|Originator', sponsor, re.IGNORECASE):
                return sponsor

    return None


def _extract_deal_source(message: str) -> Optional[str]:
    """
    Extract deal source account name from message.

    Deal source is typically the sponsor, investment bank, or lender that sent the deal.
    Looks for various patterns including:
    - Source: <name>
    - Originator: <name>
    - Deal Source: <name>
    - from <bank name>
    """
    # Try explicit source/originator field patterns
    # Use word-based patterns to avoid matching too much text
    patterns = [
        # Match "Source: Name" - capture up to reasonable length until common delimiters
        r'(?:Deal\s+)?Source:\s*([A-Za-z0-9][\w\s&\'-]{0,50}?)(?:\s+(?:Stage|Team|Sponsor|Transaction|Originator|Deal|Initial|Term|is|has|and|,|\()|$)',
        r'Originator:\s*([A-Za-z0-9][\w\s&\'-]{0,50}?)(?:\s+(?:Stage|Team|Sponsor|Transaction|Source|Deal|Initial|Term|is|has|,|\()|$)',
        # Match "from/via Bank Name" patterns
        r'(?:Sent|Received)\s+(?:from|by)\s+([A-Z][A-Za-z\s&\'-]{2,40}?)(?:\s+(?:on|at|for|,|\.|\())',
        r'(?:via|through)\s+([A-Z][A-Za-z\s&\'-]{2,40}?)(?:\s+(?:on|at|for|,|\.|\())',
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            source = match.group(1).strip()
            # Clean up common suffixes and trailing punctuation
            source = re.sub(r'\s*(LLC|LP|Inc|Corp|Securities|Bank|Capital)\.?$', '', source, flags=re.IGNORECASE)
            source = source.rstrip(' ,.:;')
            # Validate: should be reasonable length and not contain field names
            if source and 2 < len(source) <= 60 and not re.search(r'Stage|Sponsor|Team|Transaction|Originator', source, re.IGNORECASE):
                return source

    return None
