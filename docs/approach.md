# Approach

## Pipeline Overview

The data processing pipeline follows a **rules-first, LLM-fallback** approach to clean, normalize, and enrich inventory data for IPAM/DNS/DHCP workflows.

### Processing Steps (in order):

1. **IP Address Validation & Normalization** (Rules-based)

   - Validates IPv4 format using regex and range checks
   - Normalizes leading zeros (e.g., `192.168.010.005` → `192.168.10.5`)
   - Classifies IP type (private RFC1918, loopback, link-local, public)
   - Generates subnet CIDR for private IPs (/24 heuristic)

2. **Hostname Validation** (Rules-based)

   - Validates against RFC 1123 standards
   - Checks length, character set, and label format
   - Normalizes to lowercase

3. **FQDN Validation** (Rules-based)

   - Validates fully qualified domain names
   - Ensures proper TLD structure
   - Checks consistency with hostname

4. **Reverse PTR Generation** (Rules-based)

   - Generates reverse DNS records for valid IPv4 addresses
   - Format: `1.1.168.192.in-addr.arpa`

5. **MAC Address Validation & Normalization** (Rules-based)

   - Accepts multiple formats (XX:XX:XX:XX:XX:XX, XX-XX-XX-XX-XX-XX, XXXX.XXXX.XXXX)
   - Normalizes to standard colon-separated format
   - Validates hexadecimal characters

6. **Owner Parsing** (Rules-based with regex)

   - Extracts email addresses using regex patterns
   - Extracts team information from parentheses or common keywords
   - Separates owner name, email, and team into distinct fields

7. **Device Type Classification** (Rules-based with heuristics)

   - Uses explicit device_type field when available (high confidence)
   - Falls back to hostname/notes heuristics (medium confidence)
   - Maps common variations (srv→server, sw→switch, gw→router)
   - _Note: LLM integration prepared but not implemented due to API key requirements_

8. **Site Normalization** (Rules-based)
   - Standardizes abbreviations (bldg→Building, hq→HQ)
   - Normalizes separators and capitalization
   - Preserves acronyms (HQ, BLR, DC)

## Constraints

- **IPv4 Only**: IPv6 addresses are flagged as invalid (assignment scope)
- **Deterministic First**: All validation uses deterministic rules; no LLM calls in production
- **Case Sensitivity**: Hostnames/FQDNs normalized to lowercase; sites use title case
- **Missing Data**: Empty fields are preserved as empty strings, not nulls
- **Anomaly Tracking**: All validation failures logged to `anomalies.json`

## Reproduction

### Prerequisites

- Python 3.8+
- Standard library only (no external dependencies required)

### Steps

1. **Activate virtual environment** (if using):

   ```bash
   source infoblox_test_env/bin/activate
   ```

2. **Run the pipeline**:

   ```bash
   python src/run.py
   ```

3. **Outputs**:
   - `inventory_clean.csv` - Normalized inventory data
   - `anomalies.json` - Validation issues and recommendations

### Alternative: Run processor directly

```bash
python src/data_processor.py inventory_raw.csv
```

## Architecture

- **`run.py`**: Main orchestrator, calls data processor
- **`data_processor.py`**: Comprehensive processing module with all validators/normalizers
- **`run_ipv4_validation.py`**: Original IPv4 validation (imported by data_processor)

All processing is deterministic and reproducible. No external API calls or non-deterministic operations.
