from services.sf_client import (
    SalesforceClient,
    STRATEGY_VALUES,
    SECURITY_TYPE_VALUES,
    STAGE_VALUES,
    COMMON_STAGES,
)
from services.logger import logger


# Stage mapping for user-friendly names to Salesforce API values
STAGE_MAPPING = {stage.lower().replace(" ", "_"): stage for stage in STAGE_VALUES}

# Common security types for quick selection in UI
COMMON_SECURITY_TYPES = [
    "Term Loan",
    "Revolving Line of Credit",
    "Common Equity",
    "Preferred Equity",
    "Bond",
    "Fund Commitment",
    "Other",
]


def open_salesforce_modal(
    client, trigger_id, prefill_opp_id=None, prefill_opp_name=None, prefill_stage=None
):
    """
    Opens the Salesforce update modal.

    Args:
        client: Slack client
        trigger_id: Slack trigger ID for opening modal
        prefill_opp_id: Optional opportunity ID to store in private_metadata
        prefill_opp_name: Optional opportunity name to pre-fill
        prefill_stage: Optional stage to pre-select
    """
    # Build the modal blocks
    blocks = [
        {
            "type": "input",
            "block_id": "input_opp",
            "label": {"type": "plain_text", "text": "Opportunity Name"},
            "element": {
                "type": "plain_text_input",
                "action_id": "opp_name",
                "initial_value": prefill_opp_name if prefill_opp_name else "",
            },
        },
        {
            "type": "input",
            "block_id": "input_stage",
            "label": {"type": "plain_text", "text": "New Stage"},
            "element": {
                "type": "static_select",
                "action_id": "stage_select",
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "Discovery"},
                        "value": "discovery",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Negotiation"},
                        "value": "negotiation",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Closed Won"},
                        "value": "closed_won",
                    },
                ],
            },
        },
    ]

    # Pre-select stage if provided
    if prefill_stage:
        stage_lower = prefill_stage.lower().replace(" ", "_")
        blocks[1]["element"]["initial_option"] = {
            "text": {"type": "plain_text", "text": STAGE_MAPPING.get(stage_lower, prefill_stage)},
            "value": stage_lower,
        }

    # Store opportunity ID in private_metadata if provided
    private_metadata = ""
    if prefill_opp_id:
        private_metadata = prefill_opp_id

    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "sf_submission",
            "title": {"type": "plain_text", "text": "Update Salesforce"},
            "submit": {"type": "plain_text", "text": "Save Update"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "private_metadata": private_metadata,
            "blocks": blocks,
        },
    )


def handle_salesforce_submission(client, user_id, view):
    """
    Handles the submission of the Salesforce update modal.

    Args:
        client: Slack client
        user_id: User ID who submitted the form
        view: Modal view data
    """
    opp_name = view["state"]["values"]["input_opp"]["opp_name"]["value"]
    stage_text = view["state"]["values"]["input_stage"]["stage_select"][
        "selected_option"
    ]["text"]["text"]

    # Get opportunity ID from private_metadata if available
    opp_id = view.get("private_metadata", "")

    # Initialize Salesforce client
    sf_client = SalesforceClient()

    # Update the opportunity
    if opp_id:
        # We have the ID, update directly
        success = sf_client.update_opportunity_stage(opp_id, opp_name, stage_text)
    else:
        # Legacy fallback - search for the opportunity first
        opportunities = sf_client.search_opportunities(opp_name)
        if opportunities:
            opp_id = opportunities[0]["Id"]
            success = sf_client.update_opportunity_stage(opp_id, opp_name, stage_text)
        else:
            success = False

    if success:
        client.chat_postMessage(
            channel=user_id,
            text=f"✅ **Success!** I updated *{opp_name}* to stage *{stage_text}* in Salesforce.",
        )
    else:
        client.chat_postMessage(
            channel=user_id,
            text=f"❌ **Error:** Could not update *{opp_name}*. Please check the opportunity name and try again.",
        )


def handle_smart_update(client, user_id, company_name, target_stage):
    """
    Handles smart Salesforce updates with entity extraction.

    Business Logic:
    - 0 results: Send "not found" message
    - 1 result: Automatically send message with button to open pre-filled modal
    - Multiple results: Send disambiguation message with selection

    Args:
        client: Slack client
        user_id: User ID making the request
        company_name: Extracted company name
        target_stage: Extracted target stage
    """
    # Initialize Salesforce client
    sf_client = SalesforceClient()

    # Search for opportunities
    opportunities = sf_client.search_opportunities(company_name)

    if len(opportunities) == 0:
        # No results found
        client.chat_postMessage(
            channel=user_id,
            text=f"🔍 I couldn't find any opportunities for *'{company_name}'*. Please check the spelling or try a different search term.",
        )

    elif len(opportunities) == 1:
        # Single result - send message with button to open pre-filled modal
        opp = opportunities[0]
        client.chat_postMessage(
            channel=user_id,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ I found 1 opportunity for *'{company_name}'*:\n\n*{opp['Name']}*\nCurrent Stage: `{opp['StageName']}`\nClose Date: {opp['CloseDate']}",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": f"📝 Update to {target_stage}",
                            },
                            "action_id": f"smart_update_single_{opp['Id']}_{target_stage}",
                            "style": "primary",
                        }
                    ],
                },
            ],
        )

    else:
        # Multiple results - send disambiguation message
        options = []
        for opp in opportunities[:5]:  # Limit to 5 options
            options.append(
                {
                    "text": {
                        "type": "plain_text",
                        "text": f"{opp['Name']} ({opp['StageName']})",
                    },
                    "value": f"{opp['Id']}|{opp['Name']}|{target_stage}",
                }
            )

        client.chat_postMessage(
            channel=user_id,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"I found {len(opportunities)} opportunities for *'{company_name}'*. Which one would you like to update?",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "static_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select an opportunity",
                            },
                            "action_id": "smart_update_select",
                            "options": options,
                        }
                    ],
                },
            ],
        )


# ==========================================
# OPPORTUNITY CREATION FUNCTIONS
# ==========================================

def open_create_opportunity_modal(
    client,
    trigger_id,
    prefill_company=None,
    prefill_amount=None,
    prefill_stage=None,
    prefill_close_date=None,
    prefill_strategy=None,
    prefill_security_type=None,
    prefill_deal_source=None,
    prefill_sponsor=None,
    channel_id=None,
):
    """
    Opens the opportunity creation modal with pre-filled values.

    Args:
        client: Slack client
        trigger_id: Slack trigger ID for opening modal
        prefill_company: Company name to pre-fill
        prefill_amount: Deal amount to pre-fill
        prefill_stage: Stage to pre-select
        prefill_close_date: Close date to pre-fill (YYYY-MM-DD)
        prefill_strategy: Strategy to pre-select
        prefill_security_type: Security type to pre-select
        prefill_deal_source: Deal Source Account name to pre-fill
        prefill_sponsor: Primary Sponsor name to pre-fill
        channel_id: Slack channel ID (for RecordType lookup)
    """
    # Format amount for display
    amount_str = ""
    if prefill_amount:
        amount_str = str(prefill_amount)

    # Build strategy options
    strategy_options = [
        {"text": {"type": "plain_text", "text": s}, "value": s}
        for s in STRATEGY_VALUES
    ]

    # Build security type options (use common subset for cleaner UI)
    security_type_options = [
        {"text": {"type": "plain_text", "text": s}, "value": s}
        for s in COMMON_SECURITY_TYPES
    ]

    # Build stage options (use common stages for new deals)
    stage_options = [
        {"text": {"type": "plain_text", "text": s}, "value": s}
        for s in COMMON_STAGES
    ]

    # Find initial options if provided
    initial_strategy = None
    if prefill_strategy:
        for opt in strategy_options:
            if opt["value"] == prefill_strategy:
                initial_strategy = opt
                break

    initial_security_type = None
    if prefill_security_type:
        for opt in security_type_options:
            if opt["value"] == prefill_security_type:
                initial_security_type = opt
                break

    initial_stage = None
    if prefill_stage:
        for opt in stage_options:
            if opt["value"].lower() == prefill_stage.lower():
                initial_stage = opt
                break

    # Build modal blocks with all required fields
    blocks = [
        {
            "type": "input",
            "block_id": "input_opp_name",
            "label": {"type": "plain_text", "text": "Opportunity Name *"},
            "element": {
                "type": "plain_text_input",
                "action_id": "opp_name",
                "initial_value": f"{prefill_company} - New Deal" if prefill_company else "",
                "placeholder": {"type": "plain_text", "text": "e.g., Acme Corp - Q1 Expansion"},
            },
        },
        {
            "type": "input",
            "block_id": "input_strategy",
            "label": {"type": "plain_text", "text": "Strategy *"},
            "element": {
                "type": "static_select",
                "action_id": "strategy_select",
                "placeholder": {"type": "plain_text", "text": "Select a strategy"},
                "options": strategy_options,
            },
        },
        {
            "type": "input",
            "block_id": "input_security_type",
            "label": {"type": "plain_text", "text": "Security Type *"},
            "element": {
                "type": "static_select",
                "action_id": "security_type_select",
                "placeholder": {"type": "plain_text", "text": "Select security type"},
                "options": security_type_options,
            },
        },
        {
            "type": "input",
            "block_id": "input_stage",
            "label": {"type": "plain_text", "text": "Stage *"},
            "element": {
                "type": "static_select",
                "action_id": "stage_select",
                "placeholder": {"type": "plain_text", "text": "Select a stage"},
                "options": stage_options,
            },
        },
        {
            "type": "input",
            "block_id": "input_close_date",
            "label": {"type": "plain_text", "text": "Expected Close Date *"},
            "element": {
                "type": "plain_text_input",
                "action_id": "close_date",
                "initial_value": prefill_close_date if prefill_close_date else "",
                "placeholder": {"type": "plain_text", "text": "YYYY-MM-DD"},
            },
        },
        {
            "type": "input",
            "block_id": "input_amount",
            "label": {"type": "plain_text", "text": "Deal Amount ($)"},
            "optional": True,
            "element": {
                "type": "plain_text_input",
                "action_id": "amount",
                "initial_value": amount_str,
                "placeholder": {"type": "plain_text", "text": "e.g., 50000"},
            },
        },
        {
            "type": "divider",
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Account Lookups*\n_Enter the exact account name from Salesforce. If the account doesn't exist, leave blank or create the account first._",
            },
        },
        {
            "type": "input",
            "block_id": "input_deal_source",
            "label": {"type": "plain_text", "text": "Deal Source Account *"},
            "element": {
                "type": "plain_text_input",
                "action_id": "deal_source",
                "initial_value": prefill_deal_source or prefill_sponsor or "",
                "placeholder": {"type": "plain_text", "text": "e.g., Goldman Sachs, Apollo, Ares"},
            },
            "hint": {"type": "plain_text", "text": "Sponsor, bank, or lender that sent the deal"},
        },
        {
            "type": "input",
            "block_id": "input_sponsor",
            "label": {"type": "plain_text", "text": "Primary Sponsor *"},
            "element": {
                "type": "plain_text_input",
                "action_id": "sponsor",
                "initial_value": prefill_sponsor or "",
                "placeholder": {"type": "plain_text", "text": "e.g., KKR, Blackstone, Carlyle"},
            },
            "hint": {"type": "plain_text", "text": "Primary private equity sponsor on the deal"},
        },
    ]

    # Set initial options if provided
    if initial_strategy:
        blocks[1]["element"]["initial_option"] = initial_strategy
    if initial_security_type:
        blocks[2]["element"]["initial_option"] = initial_security_type
    if initial_stage:
        blocks[3]["element"]["initial_option"] = initial_stage

    # Store company name and channel_id in private_metadata for reference
    # Channel ID is used to determine the RecordType for the opportunity
    import json
    private_metadata = json.dumps({
        "company": prefill_company or "",
        "channel_id": channel_id or ""
    })

    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "sf_create_submission",
            "title": {"type": "plain_text", "text": "Create Opportunity"},
            "submit": {"type": "plain_text", "text": "Create"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "private_metadata": private_metadata,
            "blocks": blocks,
        },
    )


def handle_create_submission(client, user_id, view):
    """
    Handles the submission of the opportunity creation modal.

    Args:
        client: Slack client
        user_id: User ID who submitted the form
        view: Modal view data
    """
    import json
    from config.channel_config import channel_config

    # Parse private_metadata (contains company name and channel_id)
    private_metadata_raw = view.get("private_metadata", "{}")
    try:
        private_metadata = json.loads(private_metadata_raw)
        channel_id = private_metadata.get("channel_id", "")
    except (json.JSONDecodeError, TypeError):
        # Fallback for old format (plain string)
        channel_id = ""
        private_metadata = {"company": private_metadata_raw}

    # Extract form values
    opp_name = view["state"]["values"]["input_opp_name"]["opp_name"]["value"]
    strategy = view["state"]["values"]["input_strategy"]["strategy_select"]["selected_option"]["value"]
    security_type = view["state"]["values"]["input_security_type"]["security_type_select"]["selected_option"]["value"]
    stage = view["state"]["values"]["input_stage"]["stage_select"]["selected_option"]["value"]
    close_date = view["state"]["values"]["input_close_date"]["close_date"]["value"]

    # Amount is optional
    amount_data = view["state"]["values"]["input_amount"]["amount"]
    amount_str = amount_data.get("value") if amount_data else None

    # Extract account lookup fields
    deal_source_name = view["state"]["values"]["input_deal_source"]["deal_source"]["value"]
    sponsor_name = view["state"]["values"]["input_sponsor"]["sponsor"]["value"]

    # Parse amount
    amount = None
    if amount_str:
        try:
            amount = int(amount_str.replace(",", "").replace("$", ""))
        except (ValueError, AttributeError):
            amount = None

    # Initialize Salesforce client
    sf_client = SalesforceClient()

    # Helper function to search for account with TBD fallback
    def find_account_id(search_name: str) -> tuple:
        """
        Search for an account by name. Falls back to "TBD" if not found.
        Returns (account_id, found_name, used_tbd_fallback)
        """
        if not search_name or search_name.strip().upper() == "TBD":
            # User entered TBD directly, search for TBD account
            tbd_accounts = sf_client.search_accounts("TBD")
            if tbd_accounts:
                return (tbd_accounts[0]["Id"], "TBD", True)
            return (None, None, True)

        # Search for the specified account
        accounts = sf_client.search_accounts(search_name)
        if accounts:
            # Use exact match if found, otherwise first result
            for acc in accounts:
                if acc["Name"].lower() == search_name.lower():
                    return (acc["Id"], acc["Name"], False)
            return (accounts[0]["Id"], accounts[0]["Name"], False)

        # Not found - try TBD as fallback
        tbd_accounts = sf_client.search_accounts("TBD")
        if tbd_accounts:
            return (tbd_accounts[0]["Id"], f"TBD ('{search_name}' not found)", True)

        return (None, None, False)

    # Search for Deal Source Account
    deal_source_id, deal_source_found, deal_source_used_tbd = find_account_id(deal_source_name)

    # Search for Primary Sponsor Account
    sponsor_id, sponsor_found, sponsor_used_tbd = find_account_id(sponsor_name)

    # Build opportunity data with required fields
    opp_data = {
        "Name": opp_name,
        "Strategy__c": strategy,
        "Security_Type__c": security_type,
        "StageName": stage,
        "CloseDate": close_date,
    }

    # Add RecordTypeId based on channel if configured
    if channel_id:
        record_type_id = channel_config.get_record_type_id(channel_id)
        if record_type_id:
            opp_data["RecordTypeId"] = record_type_id
            bu_name = channel_config.get_business_unit(channel_id) or "default"
            logger.info(
                f"Setting RecordTypeId for business unit: {bu_name}",
                service="salesforce",
                channel_id=channel_id,
                business_unit=bu_name,
                record_type_id=record_type_id
            )

    # Add optional amount if provided
    if amount:
        opp_data["Amount"] = amount

    # Add account lookups if found
    if deal_source_id:
        opp_data["Deal_Source_Account__c"] = deal_source_id
    if sponsor_id:
        opp_data["Primary_Sponsor__c"] = sponsor_id

    logger.info(
        f"Creating opportunity: {opp_name}",
        service="salesforce",
        user_id=user_id,
        opp_data=opp_data,
        deal_source_found=deal_source_found,
        sponsor_found=sponsor_found,
    )

    # Create opportunity
    success, opp_id = sf_client.create_opportunity(opp_data)

    if success:
        # Format amount for display
        amount_display = f"${amount:,}" if amount else "Not specified"

        # Format account lookups for display
        deal_source_display = deal_source_found if deal_source_found else f"⚠️ Not found: '{deal_source_name}'" if deal_source_name else "Not specified"
        sponsor_display = sponsor_found if sponsor_found else f"⚠️ Not found: '{sponsor_name}'" if sponsor_name else "Not specified"

        client.chat_postMessage(
            channel=user_id,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *Opportunity Created Successfully*\n\n"
                               f"*Name:* {opp_name}\n"
                               f"*Strategy:* {strategy}\n"
                               f"*Security Type:* {security_type}\n"
                               f"*Stage:* {stage}\n"
                               f"*Close Date:* {close_date}\n"
                               f"*Amount:* {amount_display}\n"
                               f"*Deal Source:* {deal_source_display}\n"
                               f"*Primary Sponsor:* {sponsor_display}\n"
                               f"*ID:* `{opp_id}`",
                    },
                },
            ],
        )
    else:
        # Build error message with hints about account lookups
        error_hints = []
        if deal_source_name and not deal_source_id:
            error_hints.append(f"Deal Source Account '{deal_source_name}' was not found (and no 'TBD' account exists)")
        if sponsor_name and not sponsor_id:
            error_hints.append(f"Primary Sponsor '{sponsor_name}' was not found (and no 'TBD' account exists)")

        error_msg = f"❌ *Error:* Could not create opportunity *{opp_name}*."
        if error_hints:
            error_msg += "\n\n*Possible issues:*\n• " + "\n• ".join(error_hints)
            error_msg += "\n\n*Tip:* Create an Account named 'TBD' in Salesforce to use as a placeholder for unknown sponsors/sources."
        else:
            error_msg += " Please check all required fields and try again."

        client.chat_postMessage(
            channel=user_id,
            text=error_msg,
        )
