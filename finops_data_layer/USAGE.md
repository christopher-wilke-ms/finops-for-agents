# FinOps Data Layer - Usage Guide

## Installation

1. Ensure you have the `jsonschema` library installed:
```bash
pip install jsonschema
```

2. Copy the schema files to your project:
   - `schema.json` - JSON Schema definition
   - `finops_schema.py` - Python utilities

## Quick Start

### Option 1: Auto-Convert from Foundry Response

The easiest way - converts Foundry API response directly into a validated record:

```python
from finops_data_layer.finops_schema import create_from_foundry_response

# After calling Foundry agent
record = create_from_foundry_response(
    foundry_response=foundry_response_json,
    user_metadata={
        "name": "John Doe",
        "email": "john@company.com",
        "aad_object_id": "user-id-123",
        "department": "Engineering"
    },
    user_message="your original message",
    billing_account_id="your-billing-account-id"
)

# Validate
is_valid, errors = record.to_dict()
if is_valid:
    # Send to storage (Cosmos DB, App Insights, etc.)
    send_to_storage(record.to_dict())
else:
    print(f"Validation errors: {errors}")
```

### Option 2: Manual Record Construction

For more control, build records step-by-step:

```python
from finops_data_layer.finops_schema import FinOpsAgentMetrics, validate_record

record = FinOpsAgentMetrics(
    billing_account_id="99f1582e-0660-4cdb-8dac-21d7a4752603",
    billing_period_start="2026-08-01T00:00:00Z",
    billing_period_end="2026-08-31T23:59:59Z",
    charge_period_start="2026-08-25T13:47:52Z",
    charge_period_end="2026-08-25T13:47:57Z",
    service_category="AI Services",
    service_name="Microsoft Foundry",
    resource_id="super-fun-coding-learn-agent",
    resource_type="AI Agent",
    consumed_quantity=4816,
    consumed_unit="Tokens",
    effective_cost=0.43,
    user_id="bb21c6ed-b5d7-4d44-8814-85ba26bed1f5",
    user_email="admin@company.com",
    agent_id="super-fun-coding-learn-agent",
    agent_name="super-fun-coding-learn-agent",
    model_id="gpt-5-mini",
    input_tokens=4339,
    output_tokens=477,
    total_tokens=4816,
    created_at="2026-08-25T13:47:52Z",
    completed_at="2026-08-25T13:47:57Z",
    # Optional fields
    user_name="MOD Administrator",
    user_department="Engineering",
    agent_version="2",
    processing_time_seconds=5,
    tags={"environment": "production"}
)

# Validate
is_valid, errors = validate_record(record.to_dict())
if is_valid:
    print("✓ Record is valid!")
    # Convert to JSON for storage
    json_data = record.to_json()
else:
    print("✗ Validation failed:")
    for error in errors:
        print(f"  - {error}")
```

### Option 3: Direct Dictionary Validation

If you already have a dictionary:

```python
from finops_data_layer.finops_schema import validate_record

record_dict = {
    "BillingAccountId": "99f1582e-0660-4cdb-8dac-21d7a4752603",
    "x_UserEmail": "user@company.com",
    # ... other fields
}

is_valid, errors = validate_record(record_dict)
```

## Integration with bot_service.py

Add to your Flask bot handler:

```python
from finops_data_layer.finops_schema import create_from_foundry_response, validate_record

@app.route("/api/messages", methods=["POST"])
def messages():
    # ... existing code ...
    
    # After calling Foundry agent
    agent_response, agent_metadata = call_foundry_agent(user_message, user_metadata)
    
    # Create FinOps record
    finops_record = create_from_foundry_response(
        foundry_response=agent_metadata,  # Pass the full response
        user_metadata={
            "name": user_from.get('name'),
            "email": graph_user_info.get('mail'),
            "aad_object_id": aad_object_id,
            "department": graph_user_info.get('department')
        },
        user_message=user_message,
        billing_account_id="YOUR_BILLING_ACCOUNT_ID"
    )
    
    # Validate
    is_valid, errors = validate_record(finops_record.to_dict())
    if is_valid:
        # Store to Application Insights or Cosmos DB
        store_metrics(finops_record.to_dict())
    else:
        print(f"Record validation failed: {errors}")
    
    # ... rest of code ...
```

## Storage Integration

### Application Insights

```python
from azure.monitor.opentelemetry import AzureMonitorTraceLoggingOptions
from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter

# Log as custom event
client.track_event(
    name="FinOpsAgentMetrics",
    properties=finops_record.to_dict()
)
```

### Cosmos DB

```python
from azure.cosmos import CosmosClient

client = CosmosClient(connection_string)
database = client.get_database_client("finops_db")
container = database.get_container_client("agent_metrics")

# Store record
container.create_item(body=finops_record.to_dict())
```

### JSON Lines (JSONL) File

```python
import jsonlines

# Append record to JSONL file
with jsonlines.open("finops_metrics.jsonl", mode='a') as writer:
    writer.write(finops_record.to_dict())
```

## Schema Details

### Required Fields

These 21 fields are always required:

```
BillingAccountId, BillingPeriodStart, BillingPeriodEnd, ChargePeriodStart,
ChargePeriodEnd, ServiceCategory, ServiceName, ResourceId, ResourceType,
ConsumedQuantity, ConsumedUnit, EffectiveCost, x_UserId, x_UserEmail,
x_AgentId, x_AgentName, x_ModelId, x_InputTokens, x_OutputTokens,
x_TotalTokens, x_CreatedAt, x_CompletedAt
```

### Data Types

- **DateTime**: ISO 8601 format (e.g., `2026-08-25T13:47:52Z`)
- **Decimal/Number**: Float values with minimum of 0
- **Integer**: Whole numbers (token counts)
- **String**: Text values with length limits where applicable
- **JSON Object**: For Tags and metadata (ECMA 404 compliant)

### Nullable vs Required

- Fields starting with `x_` are FOCUS extensions
- Fields ending in optional parameters are nullable
- Use `None` in Python, which becomes `null` in JSON

## Validation Examples

```python
from finops_data_layer.finops_schema import validate_record

# This will fail - missing required email
record_invalid = {
    "BillingAccountId": "test",
    "x_UserId": "user-123",
    "x_UserEmail": None,  # Required!
    # ... missing other required fields
}
is_valid, errors = validate_record(record_invalid)
# Output: (False, ['x_UserEmail is required', ...])

# This will pass
record_valid = {
    "BillingAccountId": "99f1582e-0660-4cdb-8dac-21d7a4752603",
    "BillingPeriodStart": "2026-08-01T00:00:00Z",
    # ... all required fields present with correct types
}
is_valid, errors = validate_record(record_valid)
# Output: (True, [])
```

## Testing the Schema

Run the example in finops_schema.py:

```bash
python finops_data_layer/finops_schema.py
```

Expected output:
```
Schema ID: https://finops.org/schema/agents/finops-agent-metrics-v1.0.json
Title: FinOps for Agents - Agent Metrics Record

Validation result: True
  ✓ Record is valid!
```

## Troubleshooting

### ImportError: No module named 'jsonschema'

Install the library:
```bash
pip install jsonschema
```

### FileNotFoundError: Schema file not found

Ensure `schema.json` is in the same directory as `finops_schema.py`:
```
finops_data_layer/
├── README.md
├── schema.json          ← Required
├── finops_schema.py     ← Required
└── __init__.py
```

### ValidationError: Field X is required

Check that all required fields from the schema are present in your record and have the correct data type.

## References

- FOCUS Specification: https://focus.finops.org/
- JSON Schema: https://json-schema.org/
- ECMA 404 (JSON Standard): https://www.ecma-international.org/publications-and-standards/standards/ecma-404/

