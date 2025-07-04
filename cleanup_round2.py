#!/usr/bin/env python3
"""
Round 2 Database Cleanup Script - Catching remaining problematic entries
"""

import requests
import re
from typing import List, Dict

API_BASE_URL = "http://localhost:8000/api/opportunities"

def get_remaining_opportunities():
    """Get all active opportunities."""
    response = requests.get(f"{API_BASE_URL}/", params={"limit": 2000, "is_active": True})
    return response.json()

def find_remaining_problematic_entries(opportunities):
    """Find entries that should have been caught but weren't."""
    problematic_ids = []
    
    for opp in opportunities:
        title = (opp.get('title') or '').strip()
        if not title:
            continue
            
        # More specific patterns for remaining problematic entries
        if (
            # Generic "- Application Form" entries without specific program names
            re.match(r'^(program|research|website|programs?)\s+(website\s+)?-?\s*application\s+form\s*$', title, re.IGNORECASE) or
            re.match(r'^.{1,20}\s+website\s*-\s*application\s+form\s*$', title, re.IGNORECASE) or
            
            # Entries that are just "Something - Application Form" where Something is too generic
            (re.search(r'-\s*application\s+form\s*$', title, re.IGNORECASE) and 
             re.match(r'^(program|website|research|form|department|graduate programs?|pathways programs?)\s*-', title, re.IGNORECASE)) or
            
            # Specific problematic patterns we can see
            re.match(r'^pathways\s+programs?\s*-\s*application\s+form\s*$', title, re.IGNORECASE) or
            re.match(r'^graduate\s+programs?\s*-\s*application\s+form\s*$', title, re.IGNORECASE) or
            re.match(r'^interdisciplinary\s+programs?\s+website\s*-\s*application\s+form\s*$', title, re.IGNORECASE) or
            
            # Generic advice/guidance entries
            re.match(r'^(preparing\s+your\s+applications?|funding\s+graduate\s+studies|advice\s+on)', title, re.IGNORECASE) or
            
            # Very generic institute entries that don't specify programs
            (re.search(r'institute\s+for\s+research\s+in\s+the\s+social\s+sciences\s*-\s*application\s+form', title, re.IGNORECASE))
        ):
            problematic_ids.append(opp['id'])
            print(f"ROUND 2 CLEANUP - ID {opp['id']}: {title}")
    
    return problematic_ids

def main():
    print("=== ROUND 2 DATABASE CLEANUP ===")
    print("Catching remaining problematic entries...")
    
    opportunities = get_remaining_opportunities()
    print(f"Found {len(opportunities)} active opportunities")
    
    problematic_ids = find_remaining_problematic_entries(opportunities)
    
    if not problematic_ids:
        print("No additional problematic entries found!")
        return
        
    print(f"\nFound {len(problematic_ids)} additional problematic entries")
    
    confirm = input(f"Delete these {len(problematic_ids)} entries? (yes/no): ").lower().strip()
    
    if confirm in ['yes', 'y']:
        try:
            response = requests.post(
                f"{API_BASE_URL}/admin/bulk-deactivate",
                json=problematic_ids
            )
            response.raise_for_status()
            result = response.json()
            print(f"Successfully deactivated {len(problematic_ids)} additional opportunities")
            print(f"API response: {result}")
        except requests.RequestException as e:
            print(f"Error during deletion: {e}")
    else:
        print("Deletion cancelled.")

if __name__ == "__main__":
    main() 