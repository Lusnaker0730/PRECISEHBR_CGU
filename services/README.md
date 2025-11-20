# Services Directory

This directory contains the refactored microservices from the original `fhir_data_service.py`.

## Directory Structure

```
services/
├── __init__.py                      # Package initialization and exports
├── config_loader.py                 # Configuration management service
├── unit_conversion_service.py       # Laboratory value unit conversions
├── fhir_client_service.py          # FHIR server interactions
├── condition_checker.py             # Medical condition checking
├── risk_classifier.py               # Risk categorization
├── precise_hbr_calculator.py       # PRECISE-HBR risk calculation
└── tradeoff_model_calculator.py    # Bleeding-thrombosis tradeoff analysis
```

## Quick Start

### Using Individual Services

```python
# Import specific services
from services.config_loader import config_loader
from services.fhir_client_service import FHIRClientService
from services.precise_hbr_calculator import precise_hbr_calculator

# Use the services
config = config_loader.config
fhir_service = FHIRClientService(url, token, client_id)
components, score = precise_hbr_calculator.calculate_score(raw_data, demographics)
```

### Using Legacy Functions (Backward Compatible)

```python
# Import from main module
from fhir_data_service import (
    get_fhir_data,
    calculate_precise_hbr_score,
    calculate_tradeoff_scores
)

# Use legacy functions as before
raw_data, error = get_fhir_data(url, token, patient_id, client_id)
components, score = calculate_precise_hbr_score(raw_data, demographics)
```

## Service Dependencies

```
config_loader (no dependencies)
    ↓
unit_conversion_service (depends on: logging)
    ↓
condition_checker (depends on: config_loader, unit_conversion_service)
    ↓
precise_hbr_calculator (depends on: unit_conversion_service, condition_checker)
    ↓
risk_classifier (depends on: logging)
    ↓
tradeoff_model_calculator (depends on: all above services)
    ↓
fhir_client_service (depends on: config_loader, fhirclient)
```

## Testing

Each service can be tested independently:

```python
# Example: Testing unit conversion
from services.unit_conversion_service import unit_converter

obs = {'valueQuantity': {'value': 120, 'unit': 'g/l'}}
result = unit_converter.get_value_from_observation(
    obs, 
    unit_converter.TARGET_UNITS['HEMOGLOBIN']
)
print(f"Converted value: {result} g/dL")  # Output: 12.0 g/dL
```

## Documentation

See `SERVICES_ARCHITECTURE.md` in the project root for detailed documentation on:
- Service responsibilities
- Usage examples
- API reference
- Testing strategies
- Deployment recommendations

## Migration Guide

### From Monolithic to Microservices

**Old Code:**
```python
from fhir_data_service import calculate_precise_hbr_score
components, score = calculate_precise_hbr_score(raw_data, demographics)
```

**New Code (Recommended):**
```python
from services.precise_hbr_calculator import precise_hbr_calculator
components, score = precise_hbr_calculator.calculate_score(raw_data, demographics)
```

**Note:** Both approaches work! The old code is maintained for backward compatibility.

## Best Practices

1. **Import services, not internal functions** - Use the service instances (e.g., `config_loader`, `unit_converter`)
2. **Avoid circular imports** - Follow the dependency hierarchy
3. **Use type hints** - For better code clarity and IDE support
4. **Log appropriately** - Use the `logging` module for debugging
5. **Handle errors gracefully** - Each service returns `None` or empty values on error

## Contributing

When adding new functionality:
1. Determine which service is responsible
2. Add the functionality to that service
3. Update tests
4. Update documentation
5. Ensure backward compatibility if modifying existing functions

## License

Same as the parent project.

