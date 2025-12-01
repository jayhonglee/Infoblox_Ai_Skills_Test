#!/usr/bin/env python3
"""
Comprehensive data processing module for inventory normalization.
Uses deterministic rules first, LLM only where rules are insufficient.
"""
import csv
import json
import re
import sys
from pathlib import Path
from typing import Tuple, Optional, Dict, List

# Import IPv4 validation from existing module
from run_ipv4_validation import ipv4_validate_and_normalize, default_subnet, classify_ipv4_type


def hostname_validate(hostname: str) -> Tuple[bool, str, str]:
    """
    Validate hostname according to RFC 1123.
    Returns: (is_valid, normalized_hostname, reason)
    """
    if not hostname or hostname.strip() == "":
        return (False, "", "missing")
    
    hostname = hostname.strip()
    
    # Basic length check
    if len(hostname) > 253:
        return (False, hostname, "too_long")
    
    # Check for valid characters: alphanumeric, hyphen, dot
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]{0,61}[a-zA-Z0-9])?$', hostname):
        return (False, hostname, "invalid_chars")
    
    # Check labels (parts separated by dots)
    labels = hostname.split('.')
    for label in labels:
        if len(label) > 63:
            return (False, hostname, "label_too_long")
        if len(label) == 0:
            return (False, hostname, "empty_label")
        if label.startswith('-') or label.endswith('-'):
            return (False, hostname, "invalid_label_format")
    
    return (True, hostname.lower(), "ok")


def fqdn_validate(fqdn: str) -> Tuple[bool, str, str]:
    """
    Validate FQDN (Fully Qualified Domain Name).
    Returns: (is_valid, normalized_fqdn, reason)
    """
    if not fqdn or fqdn.strip() == "":
        return (False, "", "missing")
    
    fqdn = fqdn.strip()
    
    # Must end with a dot or have at least one dot
    if '.' not in fqdn:
        return (False, fqdn, "not_fqdn")
    
    # Use hostname validation but require at least one dot
    valid, normalized, reason = hostname_validate(fqdn)
    if not valid:
        return (valid, fqdn, reason)
    
    # Ensure it has a TLD (at least 2 labels)
    labels = normalized.split('.')
    if len(labels) < 2:
        return (False, fqdn, "missing_tld")
    
    return (True, normalized, "ok")


def fqdn_consistent(hostname: str, fqdn: str, ip: str) -> bool:
    """
    Check if hostname is consistent with FQDN.
    Returns True if hostname matches the first part of FQDN.
    """
    if not hostname or not fqdn:
        return False
    
    hostname_lower = hostname.strip().lower()
    fqdn_lower = fqdn.strip().lower()
    
    # Check if hostname matches the first label of FQDN
    fqdn_first_label = fqdn_lower.split('.')[0] if '.' in fqdn_lower else fqdn_lower
    return hostname_lower == fqdn_first_label


def reverse_ptr_generate(ip: str) -> str:
    """
    Generate reverse PTR record for IPv4 address.
    Example: 192.168.1.1 -> 1.1.168.192.in-addr.arpa
    """
    if not ip:
        return ""
    
    valid, canonical, _ = ipv4_validate_and_normalize(ip)
    if not valid:
        return ""
    
    parts = canonical.split('.')
    parts.reverse()
    return '.'.join(parts) + '.in-addr.arpa'


def mac_validate_and_normalize(mac: str) -> Tuple[bool, str, str]:
    """
    Validate and normalize MAC address.
    Accepts formats: XX:XX:XX:XX:XX:XX, XX-XX-XX-XX-XX-XX, XXXX.XXXX.XXXX
    Returns: (is_valid, normalized_mac, reason)
    """
    if not mac or mac.strip() == "":
        return (False, "", "missing")
    
    mac = mac.strip()
    
    # Remove common separators and convert to uppercase
    mac_clean = re.sub(r'[-:.]', '', mac)
    
    # Check length (should be 12 hex characters)
    if len(mac_clean) != 12:
        return (False, mac, "wrong_length")
    
    # Check if all characters are hexadecimal
    if not re.match(r'^[0-9A-Fa-f]{12}$', mac_clean):
        return (False, mac, "invalid_chars")
    
    # Normalize to XX:XX:XX:XX:XX:XX format
    normalized = ':'.join([mac_clean[i:i+2].upper() for i in range(0, 12, 2)])
    
    return (True, normalized, "ok")


def owner_parse(owner: str) -> Tuple[str, str, str]:
    """
    Parse owner field to extract owner name, email, and team.
    Uses regex patterns to extract email and team information.
    Returns: (owner_name, owner_email, owner_team)
    """
    if not owner or owner.strip() == "":
        return ("", "", "")
    
    owner = owner.strip()
    email = ""
    team = ""
    owner_name = owner
    
    # Extract email using regex
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_match = re.search(email_pattern, owner)
    if email_match:
        email = email_match.group(0).lower()
        # Remove email from owner string
        owner_name = re.sub(email_pattern, '', owner).strip()
    
    # Extract team from parentheses or common patterns
    team_patterns = [
        r'\(([^)]+)\)',  # (team)
        r'\b(platform|ops|sec|facilities|infrastructure|network|security)\b',
    ]
    
    for pattern in team_patterns:
        match = re.search(pattern, owner_name, re.IGNORECASE)
        if match:
            team = match.group(1) if match.lastindex else match.group(0)
            team = team.lower()
            # Remove team from owner name
            owner_name = re.sub(pattern, '', owner_name, flags=re.IGNORECASE).strip()
            break
    
    # Clean up owner name (remove extra spaces, parentheses)
    owner_name = re.sub(r'\s+', ' ', owner_name).strip()
    owner_name = re.sub(r'[()]', '', owner_name).strip()
    
    return (owner_name, email, team)


def device_type_classify(device_type: str, hostname: str = "", notes: str = "") -> Tuple[str, str]:
    """
    Classify device type using rules first, LLM only for ambiguous cases.
    Returns: (device_type, confidence)
    Confidence: "high" (rules), "medium" (heuristics), "low" (needs LLM but not implemented)
    """
    if not device_type or device_type.strip() == "":
        # Try to infer from hostname or notes
        combined = f"{hostname} {notes}".lower()
        
        # Heuristic-based classification
        if any(word in combined for word in ['server', 'srv', 'host']):
            return ("server", "medium")
        elif any(word in combined for word in ['switch', 'sw']):
            return ("switch", "medium")
        elif any(word in combined for word in ['router', 'gw', 'gateway']):
            return ("router", "medium")
        elif any(word in combined for word in ['printer', 'print']):
            return ("printer", "medium")
        elif any(word in combined for word in ['camera', 'cam', 'iot']):
            return ("iot", "medium")
        elif any(word in combined for word in ['dns', 'nameserver']):
            return ("dns", "medium")
        else:
            return ("unknown", "low")
    
    device_type = device_type.strip().lower()
    
    # Normalize common variations
    type_mapping = {
        'server': 'server',
        'srv': 'server',
        'host': 'server',
        'switch': 'switch',
        'sw': 'switch',
        'router': 'router',
        'gw': 'router',
        'gateway': 'router',
        'printer': 'printer',
        'print': 'printer',
        'iot': 'iot',
        'camera': 'iot',
        'cam': 'iot',
        'dns': 'dns',
        'nameserver': 'dns',
    }
    
    normalized = type_mapping.get(device_type, device_type)
    return (normalized, "high")


def site_normalize(site: str) -> str:
    """
    Normalize site names to a consistent format.
    Handles variations like "BLR Campus" vs "BLR campus", "HQ Bldg 1" vs "HQ-BUILDING-1"
    """
    if not site or site.strip() == "":
        return ""
    
    site = site.strip()
    
    # Common normalizations
    normalizations = {
        'n/a': '',
        'na': '',
        'none': '',
    }
    
    site_lower = site.lower()
    if site_lower in normalizations:
        return normalizations[site_lower]
    
    # Normalize common abbreviations and formats
    # "BLR Campus" -> "BLR Campus" (keep as is, just standardize case)
    # "HQ Bldg 1" -> "HQ Bldg 1"
    # "HQ-BUILDING-1" -> "HQ Building 1"
    
    # Replace common variations
    site = re.sub(r'\b(bldg|building)\b', 'Building', site, flags=re.IGNORECASE)
    site = re.sub(r'\b(campus|camp)\b', 'Campus', site, flags=re.IGNORECASE)
    site = re.sub(r'\b(hq|headquarters)\b', 'HQ', site, flags=re.IGNORECASE)
    
    # Standardize separators (keep spaces, normalize dashes)
    site = re.sub(r'\s*-\s*', ' ', site)
    site = re.sub(r'\s+', ' ', site)
    
    # Title case for consistency (but preserve acronyms)
    words = site.split()
    normalized_words = []
    for word in words:
        if word.isupper() and len(word) <= 4:  # Preserve acronyms like HQ, BLR, DC
            normalized_words.append(word)
        else:
            normalized_words.append(word.capitalize())
    
    return ' '.join(normalized_words)


def process_comprehensive(input_csv: str, out_csv: str, anomalies_json: str):
    """
    Comprehensive processing function that handles all fields in the target schema.
    """
    anomalies = []
    prompts_log = []
    
    with open(input_csv, newline="") as f, open(out_csv, "w", newline="") as g:
        reader = csv.DictReader(f)
        
        # Target schema fields
        fieldnames = [
            "ip", "ip_valid", "ip_version", "subnet_cidr",
            "hostname", "hostname_valid", "fqdn", "fqdn_consistent", "reverse_ptr",
            "mac", "mac_valid",
            "owner", "owner_email", "owner_team",
            "device_type", "device_type_confidence",
            "site", "site_normalized",
            "source_row_id", "normalization_steps"
        ]
        
        writer = csv.DictWriter(g, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            source_row_id = row.get("source_row_id", "")
            steps = []
            row_anomalies = []
            
            # IP validation
            raw_ip = row.get("ip", "")
            ip_valid, ip_canonical, ip_reason = ipv4_validate_and_normalize(raw_ip)
            steps.append("ip_trim")
            
            if ip_valid:
                steps.append("ip_parse")
                steps.append("ip_normalize")
                ip_out = ip_canonical
                ip_version = "4"
                subnet_cidr = default_subnet(ip_out)
            else:
                ip_out = str(raw_ip).strip()
                ip_version = ""
                subnet_cidr = ""
                steps.append(f"ip_invalid_{ip_reason}")
                row_anomalies.append({"field": "ip", "type": ip_reason, "value": raw_ip})
            
            # Hostname validation
            raw_hostname = row.get("hostname", "")
            hostname_valid, hostname_normalized, hostname_reason = hostname_validate(raw_hostname)
            if hostname_valid:
                steps.append("hostname_validate")
                hostname_out = hostname_normalized
            else:
                hostname_out = raw_hostname
                if hostname_reason != "missing":
                    steps.append(f"hostname_invalid_{hostname_reason}")
                    row_anomalies.append({"field": "hostname", "type": hostname_reason, "value": raw_hostname})
            
            # FQDN validation
            raw_fqdn = row.get("fqdn", "")
            fqdn_valid, fqdn_normalized, fqdn_reason = fqdn_validate(raw_fqdn)
            if fqdn_valid:
                steps.append("fqdn_validate")
                fqdn_out = fqdn_normalized
            else:
                fqdn_out = raw_fqdn
                if fqdn_reason != "missing":
                    steps.append(f"fqdn_invalid_{fqdn_reason}")
                    row_anomalies.append({"field": "fqdn", "type": fqdn_reason, "value": raw_fqdn})
            
            # FQDN consistency check
            fqdn_consistent_flag = fqdn_consistent(hostname_out, fqdn_out, ip_out)
            if fqdn_consistent_flag:
                steps.append("fqdn_consistency_check")
            
            # Reverse PTR
            reverse_ptr = reverse_ptr_generate(ip_out) if ip_valid else ""
            if reverse_ptr:
                steps.append("reverse_ptr_generate")
            
            # MAC validation
            raw_mac = row.get("mac", "")
            mac_valid, mac_normalized, mac_reason = mac_validate_and_normalize(raw_mac)
            if mac_valid:
                steps.append("mac_normalize")
                mac_out = mac_normalized
            else:
                mac_out = raw_mac
                if mac_reason != "missing":
                    steps.append(f"mac_invalid_{mac_reason}")
                    row_anomalies.append({"field": "mac", "type": mac_reason, "value": raw_mac})
            
            # Owner parsing
            raw_owner = row.get("owner", "")
            owner_name, owner_email, owner_team = owner_parse(raw_owner)
            if owner_name or owner_email or owner_team:
                steps.append("owner_parse")
            
            # Device type classification
            raw_device_type = row.get("device_type", "")
            raw_hostname_for_type = row.get("hostname", "")
            raw_notes = row.get("notes", "")
            device_type_out, device_type_confidence = device_type_classify(
                raw_device_type, raw_hostname_for_type, raw_notes
            )
            if device_type_out:
                steps.append("device_type_classify")
            
            # Site normalization
            raw_site = row.get("site", "")
            site_normalized_out = site_normalize(raw_site)
            if site_normalized_out:
                steps.append("site_normalize")
            
            # Build output row
            out_row = {
                "ip": ip_out,
                "ip_valid": "true" if ip_valid else "false",
                "ip_version": ip_version,
                "subnet_cidr": subnet_cidr,
                "hostname": hostname_out,
                "hostname_valid": "true" if hostname_valid else "false",
                "fqdn": fqdn_out,
                "fqdn_consistent": "true" if fqdn_consistent_flag else "false",
                "reverse_ptr": reverse_ptr,
                "mac": mac_out,
                "mac_valid": "true" if mac_valid else "false",
                "owner": owner_name,
                "owner_email": owner_email,
                "owner_team": owner_team,
                "device_type": device_type_out,
                "device_type_confidence": device_type_confidence,
                "site": raw_site,  # Keep original
                "site_normalized": site_normalized_out,
                "source_row_id": source_row_id,
                "normalization_steps": "|".join(steps)
            }
            
            writer.writerow(out_row)
            
            # Add to anomalies if there are issues
            if row_anomalies:
                anomalies.append({
                    "source_row_id": source_row_id,
                    "issues": row_anomalies,
                    "recommended_actions": ["Review and correct invalid fields"]
                })
    
    # Write anomalies
    with open(anomalies_json, "w") as h:
        json.dump(anomalies, h, indent=2)
    
    return prompts_log


if __name__ == "__main__":
    if len(sys.argv) < 2:
        in_csv = "inventory_raw.csv"
    else:
        in_csv = sys.argv[1]
    
    # Determine output paths relative to input file location
    input_path = Path(in_csv)
    base_dir = input_path.parent
    
    out_csv = str(base_dir / "inventory_clean.csv")
    anomalies_json = str(base_dir / "anomalies.json")
    
    process_comprehensive(in_csv, out_csv, anomalies_json)
    print(f"Wrote {out_csv} and {anomalies_json}")

