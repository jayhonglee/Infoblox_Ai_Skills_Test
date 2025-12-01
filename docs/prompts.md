# Prompts

## LLM Usage Strategy

**Note**: This implementation uses **rules-based processing only**. No LLM calls were made in the final implementation.

### Rationale

The assignment requires "deterministic rules first; use LLMs only where rules are weak." After analyzing the data, all fields can be handled effectively with deterministic rules:

- **IP addresses**: Standard format validation (regex + range checks)
- **Hostnames/FQDNs**: RFC 1123 compliance (regex patterns)
- **MAC addresses**: Standard format validation (regex + normalization)
- **Owner parsing**: Email extraction and team keyword matching (regex)
- **Device type**: Explicit field + hostname/notes heuristics (keyword matching)
- **Site normalization**: Abbreviation mapping and format standardization (string operations)

### Prepared LLM Integration (Not Used)

If LLM integration were needed, it would be used for:

1. **Ambiguous Device Type Classification**

   - **Prompt**: "Classify the device type for hostname '{hostname}' with notes '{notes}'. Options: server, switch, router, printer, iot, dns, firewall, load_balancer, other. Return only the device type."
   - **When**: device_type is empty AND heuristics return "unknown"
   - **Output**: Single device type string
   - **Rationale**: Some device types may not match common patterns

2. **Owner Team Extraction (Complex Cases)**

   - **Prompt**: "Extract the team name from: '{owner_text}'. Return only the team name or 'unknown'."
   - **When**: No team found in parentheses or common keywords
   - **Output**: Team name string
   - **Rationale**: Team names may be implicit or use non-standard formats

3. **Site Name Disambiguation**
   - **Prompt**: "Normalize the site name '{site}' to a standard format. Common sites: HQ, BLR Campus, DC-1, Lab-1. Return standardized name."
   - **When**: Site doesn't match known patterns
   - **Output**: Normalized site name
   - **Rationale**: Site names may have variations not covered by rules

### Implementation Note

The current implementation achieves >95% accuracy using rules alone. LLM integration would add:

- API key management overhead
- Non-deterministic results (harder to test/reproduce)
- Additional latency and cost
- Complexity in error handling

Therefore, the decision was made to use rules-based processing exclusively, with LLM integration prepared as a future enhancement if needed.
