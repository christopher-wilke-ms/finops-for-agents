"""
FinOps for Agents - Data Layer Package

A standardized, FOCUS-compliant data model for tracking AI agent usage and costs.

This package provides:
- JSON Schema definition for agent metrics
- Python utilities for record validation and construction
- Integration helpers for Foundry agent responses
- Storage adapters for various backends

Example:
    from finops_data_layer import create_from_foundry_response, validate_record

    record = create_from_foundry_response(
        foundry_response=api_response,
        user_metadata=user_info,
        user_message="user query",
        billing_account_id="account-123"
    )

    is_valid, errors = validate_record(record.to_dict())
    if is_valid:
        store_metrics(record.to_dict())
"""

from finops_schema import (
    FinOpsAgentMetrics,
    SchemaValidator,
    validate_record,
    create_from_foundry_response,
)

__version__ = "1.0.0"
__author__ = "FinOps for Agents Team"

__all__ = [
    "FinOpsAgentMetrics",
    "SchemaValidator",
    "validate_record",
    "create_from_foundry_response",
]
