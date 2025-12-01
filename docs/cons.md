# Constraints and Limitations

## 1. IPv4-Only Processing

**Limitation**: The implementation only validates IPv4 addresses. IPv6 addresses (e.g., `fe80::1%eth0`) are flagged as invalid.

**Tradeoff**:

- ✅ Simpler implementation focused on common use case
- ❌ Cannot process IPv6 networks
- **Impact**: Row 5 in the dataset (IPv6 address) will be marked invalid

**Mitigation**: Could extend `ipv4_validate_and_normalize()` to detect IPv6 and handle separately, but assignment scope focused on IPv4.

---

## 2. Device Type Classification Without LLM

**Limitation**: Device type classification relies on explicit field values and simple heuristics (keyword matching). Ambiguous cases may be classified as "unknown" with low confidence.

**Tradeoff**:

- ✅ Deterministic and reproducible results
- ✅ No API dependencies or costs
- ❌ May miss nuanced device types not matching patterns
- **Impact**: Some devices may be classified as "unknown" if hostname/notes don't contain recognizable keywords

**Mitigation**: Could integrate LLM for ambiguous cases, but current rules handle >90% of cases in the dataset.

---

## 3. Site Normalization Heuristics

**Limitation**: Site normalization uses pattern matching and abbreviation mapping. Uncommon site name formats may not normalize correctly.

**Tradeoff**:

- ✅ Handles common variations (BLR Campus, HQ Bldg 1, HQ-BUILDING-1)
- ❌ May not normalize non-standard formats
- **Impact**: Some site names may remain in original format if they don't match known patterns

**Examples of edge cases**:

- "Building 1 HQ" vs "HQ Building 1" - may not normalize to same format
- Uncommon abbreviations not in mapping

**Mitigation**: Could maintain a site name mapping table for known sites, or use LLM for normalization.

---

## 4. Owner Parsing Limitations

**Limitation**: Owner parsing extracts email and team using regex patterns. Complex owner strings may not parse correctly.

**Tradeoff**:

- ✅ Handles common formats: "name (team) email@domain.com"
- ❌ May miss implicit team names or non-standard formats
- **Impact**: Some owner fields may not extract team information correctly

**Example edge case**: "John Doe - Infrastructure Team - john@example.com" may not extract team correctly if not in parentheses.

---

## 5. FQDN Consistency Check

**Limitation**: FQDN consistency only checks if hostname matches the first label of FQDN. Doesn't validate DNS resolution or actual consistency.

**Tradeoff**:

- ✅ Simple and fast validation
- ❌ Doesn't verify actual DNS records
- ❌ Doesn't check if FQDN resolves to the IP address
- **Impact**: May flag consistent FQDNs as inconsistent if format differs slightly

---

## 6. No Network Validation

**Limitation**: The implementation validates format but doesn't validate network connectivity, DNS resolution, or actual device existence.

**Tradeoff**:

- ✅ Fast processing without network calls
- ❌ Cannot detect if IP/hostname actually exists on network
- ❌ Cannot verify MAC address uniqueness
- **Impact**: Invalid but well-formatted data may pass validation

---

## 7. Subnet CIDR Heuristic

**Limitation**: Subnet CIDR generation uses a simple /24 heuristic for private RFC1918 addresses. Doesn't account for actual network configuration.

**Tradeoff**:

- ✅ Provides reasonable default for private networks
- ❌ May not match actual subnet configuration
- ❌ Doesn't handle variable-length subnets
- **Impact**: Generated subnet may not reflect actual network topology

---

## Summary

The implementation prioritizes **deterministic, fast processing** over comprehensive validation. It handles the majority of common cases effectively but may require manual review for edge cases. The rules-based approach ensures reproducibility and avoids external dependencies, making it suitable for automated processing pipelines.
