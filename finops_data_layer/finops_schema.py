"""
FinOps for Agents - Data Model Validator and Utilities

This module provides utilities for working with the FinOps for Agents data model,
including validation against the JSON Schema and record construction.

Example usage:
    from finops_schema import FinOpsAgentMetrics, validate_record

    # Create a record
    record = FinOpsAgentMetrics(
        billing_account_id="99f1582e-0660-4cdb-8dac-21d7a4752603",
        user_email="user@example.com",
        ...
    )

    # Validate
    is_valid = validate_record(record.to_dict())
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path


class FinOpsAgentMetrics:
    """Builder class for FinOps for Agents metrics records."""

    def __init__(
        self,
        billing_account_id: str,
        billing_period_start: str,
        billing_period_end: str,
        charge_period_start: str,
        charge_period_end: str,
        service_category: str,
        service_name: str,
        resource_id: str,
        resource_type: str,
        consumed_quantity: float,
        consumed_unit: str,
        effective_cost: float,
        user_id: str,
        user_email: str,
        agent_id: str,
        agent_name: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        created_at: str,
        completed_at: str,
        # Optional fields
        billing_account_name: Optional[str] = None,
        billing_currency: Optional[str] = "USD",
        service_subcategory: Optional[str] = None,
        sku_id: Optional[str] = None,
        sku_meter_name: Optional[str] = None,
        resource_name: Optional[str] = None,
        list_cost: Optional[float] = None,
        list_unit_price: Optional[float] = None,
        billed_cost: Optional[float] = None,
        pricing_quantity: Optional[float] = None,
        pricing_unit: Optional[str] = None,
        user_name: Optional[str] = None,
        user_department: Optional[str] = None,
        cost_center: Optional[str] = None,
        team_id: Optional[str] = None,
        project_id: Optional[str] = None,
        agent_version: Optional[str] = None,
        model_name: Optional[str] = None,
        model_family: Optional[str] = None,
        reasoning_tokens: Optional[int] = None,
        tokens_per_second: Optional[float] = None,
        processing_time_seconds: Optional[float] = None,
        request_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
        interaction_type: Optional[str] = None,
        channel: Optional[str] = None,
        region_id: Optional[str] = None,
        region_name: Optional[str] = None,
        availability_zone: Optional[str] = None,
    ):
        """Initialize a FinOps agent metrics record."""
        self.billing_account_id = billing_account_id
        self.billing_account_name = billing_account_name
        self.billing_period_start = billing_period_start
        self.billing_period_end = billing_period_end
        self.billing_currency = billing_currency
        self.charge_period_start = charge_period_start
        self.charge_period_end = charge_period_end
        self.service_category = service_category
        self.service_name = service_name
        self.service_subcategory = service_subcategory
        self.sku_id = sku_id
        self.sku_meter_name = sku_meter_name
        self.resource_id = resource_id
        self.resource_name = resource_name
        self.resource_type = resource_type
        self.list_cost = list_cost
        self.list_unit_price = list_unit_price
        self.effective_cost = effective_cost
        self.billed_cost = billed_cost
        self.consumed_quantity = consumed_quantity
        self.consumed_unit = consumed_unit
        self.pricing_quantity = pricing_quantity
        self.pricing_unit = pricing_unit
        self.user_id = user_id
        self.user_email = user_email
        self.user_name = user_name
        self.user_department = user_department
        self.cost_center = cost_center
        self.team_id = team_id
        self.project_id = project_id
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_version = agent_version
        self.model_id = model_id
        self.model_name = model_name
        self.model_family = model_family
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.reasoning_tokens = reasoning_tokens
        self.total_tokens = total_tokens
        self.tokens_per_second = tokens_per_second
        self.created_at = created_at
        self.completed_at = completed_at
        self.processing_time_seconds = processing_time_seconds
        self.request_id = request_id
        self.tags = tags or {}
        self.interaction_type = interaction_type or "Chat Message"
        self.channel = channel or "Microsoft Teams"
        self.region_id = region_id
        self.region_name = region_name
        self.availability_zone = availability_zone

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary, excluding None values."""
        data = {
            "BillingAccountId": self.billing_account_id,
            "BillingPeriodStart": self.billing_period_start,
            "BillingPeriodEnd": self.billing_period_end,
            "ChargePeriodStart": self.charge_period_start,
            "ChargePeriodEnd": self.charge_period_end,
            "ServiceCategory": self.service_category,
            "ServiceName": self.service_name,
            "ResourceId": self.resource_id,
            "ResourceType": self.resource_type,
            "ConsumedQuantity": self.consumed_quantity,
            "ConsumedUnit": self.consumed_unit,
            "EffectiveCost": self.effective_cost,
            "x_UserId": self.user_id,
            "x_UserEmail": self.user_email,
            "x_AgentId": self.agent_id,
            "x_AgentName": self.agent_name,
            "x_ModelId": self.model_id,
            "x_InputTokens": self.input_tokens,
            "x_OutputTokens": self.output_tokens,
            "x_TotalTokens": self.total_tokens,
            "x_CreatedAt": self.created_at,
            "x_CompletedAt": self.completed_at,
        }

        # Add optional fields if present
        optional_fields = {
            "BillingAccountName": self.billing_account_name,
            "BillingCurrency": self.billing_currency,
            "ServiceSubcategory": self.service_subcategory,
            "SkuId": self.sku_id,
            "SkuMeterName": self.sku_meter_name,
            "ResourceName": self.resource_name,
            "ListCost": self.list_cost,
            "ListUnitPrice": self.list_unit_price,
            "BilledCost": self.billed_cost,
            "PricingQuantity": self.pricing_quantity,
            "PricingUnit": self.pricing_unit,
            "x_UserName": self.user_name,
            "x_UserDepartment": self.user_department,
            "x_CostCenter": self.cost_center,
            "x_TeamId": self.team_id,
            "x_ProjectId": self.project_id,
            "x_AgentVersion": self.agent_version,
            "x_ModelName": self.model_name,
            "x_ModelFamily": self.model_family,
            "x_ReasoningTokens": self.reasoning_tokens,
            "x_TokensPerSecond": self.tokens_per_second,
            "x_ProcessingTimeSeconds": self.processing_time_seconds,
            "x_RequestId": self.request_id,
            "x_InteractionType": self.interaction_type,
            "x_Channel": self.channel,
            "RegionId": self.region_id,
            "RegionName": self.region_name,
            "x_AvailabilityZone": self.availability_zone,
        }

        for key, value in optional_fields.items():
            if value is not None:
                data[key] = value

        if self.tags:
            data["Tags"] = self.tags

        return data

    def to_json(self) -> str:
        """Convert record to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class SchemaValidator:
    """Validator for FinOps agent metrics records against JSON Schema."""

    _schema = None

    @classmethod
    def load_schema(cls) -> Dict[str, Any]:
        """Load the JSON Schema from file."""
        if cls._schema is None:
            schema_path = Path(__file__).parent / "schema.json"
            try:
                with open(schema_path, "r") as f:
                    cls._schema = json.load(f)
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Schema file not found at {schema_path}. "
                    "Ensure schema.json is in the finops_data_layer directory."
                )
        return cls._schema

    @classmethod
    def validate(cls, record: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate a record against the schema.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            import jsonschema
        except ImportError:
            raise ImportError(
                "jsonschema library is required. "
                "Install it with: pip install jsonschema"
            )

        schema = cls.load_schema()
        errors = []

        try:
            jsonschema.validate(instance=record, schema=schema)
            return True, []
        except jsonschema.ValidationError as e:
            return False, [str(e)]
        except jsonschema.SchemaError as e:
            return False, [f"Schema error: {str(e)}"]


def validate_record(record: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate a record dictionary against the schema.

    Args:
        record: Dictionary containing the record data

    Returns:
        Tuple of (is_valid, error_messages)
    """
    return SchemaValidator.validate(record)


def create_from_foundry_response(
    foundry_response: Dict[str, Any],
    user_metadata: Dict[str, Any],
    user_message: str,
    billing_account_id: str,
) -> FinOpsAgentMetrics:
    """
    Create a FinOpsAgentMetrics record from a Foundry agent response.

    Args:
        foundry_response: Response from Foundry agent API
        user_metadata: User metadata (from Teams + Graph API)
        user_message: Original user message
        billing_account_id: Billing account ID

    Returns:
        FinOpsAgentMetrics record
    """
    from datetime import datetime

    # Extract timestamps
    created_at = foundry_response.get("created_at")
    completed_at = foundry_response.get("completed_at")

    # Convert Unix timestamps to ISO 8601 if needed
    if isinstance(created_at, (int, float)):
        created_at_iso = datetime.fromtimestamp(created_at).isoformat() + "Z"
    else:
        created_at_iso = created_at or datetime.now().isoformat() + "Z"

    if isinstance(completed_at, (int, float)):
        completed_at_iso = datetime.fromtimestamp(completed_at).isoformat() + "Z"
    else:
        completed_at_iso = completed_at or datetime.now().isoformat() + "Z"

    # Calculate processing time
    processing_time = 0
    if isinstance(created_at, (int, float)) and isinstance(completed_at, (int, float)):
        processing_time = completed_at - created_at

    # Extract token usage
    usage = foundry_response.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    reasoning_tokens = None

    if "output_tokens_details" in usage:
        reasoning_tokens = usage["output_tokens_details"].get("reasoning_tokens")

    total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

    # Extract agent info
    agent_ref = foundry_response.get("agent_reference", {})
    agent_name = agent_ref.get("name", "unknown")
    agent_version = agent_ref.get("version", "unknown")

    # Calculate cost (placeholder - requires pricing config)
    # For now, we'll estimate based on token counts
    input_price = 0.00001  # $0.00001 per input token (example)
    output_price = 0.00003  # $0.00003 per output token (example)
    estimated_cost = (input_tokens * input_price) + (output_tokens * output_price)

    # Now create billing period dates (current month)
    now = datetime.now()
    billing_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        billing_end = billing_start.replace(year=now.year + 1, month=1)
    else:
        billing_end = billing_start.replace(month=now.month + 1)

    return FinOpsAgentMetrics(
        billing_account_id=billing_account_id,
        billing_account_name="Contoso FinOps Hackathon",
        billing_period_start=billing_start.isoformat() + "Z",
        billing_period_end=billing_end.isoformat() + "Z",
        billing_currency="USD",
        charge_period_start=created_at_iso,
        charge_period_end=completed_at_iso,
        service_category="AI Services",
        service_name="Microsoft Foundry",
        service_subcategory="AI Agents",
        sku_id=foundry_response.get("model", "unknown"),
        sku_meter_name="Token Processing",
        resource_id=agent_name,
        resource_name=agent_name,
        resource_type="AI Agent",
        list_cost=estimated_cost,
        list_unit_price=output_price,
        effective_cost=estimated_cost,
        billed_cost=estimated_cost,
        consumed_quantity=total_tokens,
        consumed_unit="Tokens",
        pricing_quantity=total_tokens / 1000,
        pricing_unit="Thousand Tokens",
        user_id=user_metadata.get("aad_object_id", "N/A"),
        user_email=user_metadata.get("email", "N/A"),
        user_name=user_metadata.get("name", "N/A"),
        user_department=user_metadata.get("department", "N/A"),
        agent_id=agent_name,
        agent_name=agent_name,
        agent_version=str(agent_version),
        model_id=foundry_response.get("model", "unknown"),
        model_name=f"GPT Model ({foundry_response.get('model', 'unknown')})",
        model_family="OpenAI",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        total_tokens=total_tokens,
        tokens_per_second=total_tokens / processing_time if processing_time > 0 else 0,
        created_at=created_at_iso,
        completed_at=completed_at_iso,
        processing_time_seconds=processing_time,
        request_id=foundry_response.get("id", "unknown"),
        tags={"source": "teams_agent", "version": "1.0"},
        interaction_type="Chat Message",
        channel="Microsoft Teams",
        region_id="swedencentral",
        region_name="Sweden Central",
    )


if __name__ == "__main__":
    # Example usage
    validator = SchemaValidator()

    # Load and display schema
    schema = validator.load_schema()
    print(f"Schema ID: {schema.get('$id')}")
    print(f"Title: {schema.get('title')}")

    # Create example record
    example_record = FinOpsAgentMetrics(
        billing_account_id="test-account-123",
        billing_period_start="2026-08-01T00:00:00Z",
        billing_period_end="2026-08-31T23:59:59Z",
        charge_period_start="2026-08-25T13:47:52Z",
        charge_period_end="2026-08-25T13:47:57Z",
        service_category="AI Services",
        service_name="Microsoft Foundry",
        resource_id="test-agent",
        resource_type="AI Agent",
        consumed_quantity=1000,
        consumed_unit="Tokens",
        effective_cost=0.10,
        user_id="user-123",
        user_email="user@example.com",
        agent_id="test-agent",
        agent_name="test-agent",
        model_id="gpt-5-mini",
        input_tokens=800,
        output_tokens=200,
        total_tokens=1000,
        created_at="2026-08-25T13:47:52Z",
        completed_at="2026-08-25T13:47:57Z",
    )

    # Validate
    is_valid, errors = validate_record(example_record.to_dict())
    print(f"\nValidation result: {is_valid}")
    if errors:
        for error in errors:
            print(f"  - {error}")
    else:
        print("  ✓ Record is valid!")
