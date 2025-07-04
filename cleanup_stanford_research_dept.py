#!/usr/bin/env python3
"""
Cleanup Script: Remove entries with department "Stanford Research"
These entries are too generic and represent navigation/administrative content rather than specific opportunities.
"""

import requests
import json

API_BASE_URL = "http://localhost:8000/api/opportunities"

def get_stanford_research_entries():
    """Get all active opportunities with department 'Stanford Research'."""
    response = requests.get(f"{API_BASE_URL}/", params={"limit": 2000, "is_active": True})
    all_opportunities = response.json()
    
    stanford_research_entries = []
    for opp in all_opportunities:
        if opp.get('department') == 'Stanford Research':
            stanford_research_entries.append(opp)
    
    return stanford_research_entries

def main():
    print("=== CLEANUP: STANFORD RESEARCH DEPARTMENT ENTRIES ===")
    print("Removing entries with department 'Stanford Research' as they are too generic")
    print()
    
    # Get all Stanford Research entries
    entries = get_stanford_research_entries()
    print(f"Found {len(entries)} entries with department 'Stanford Research'")
    
    if not entries:
        print("No entries found with department 'Stanford Research'")
        return
    
    # Show sample of what will be deleted
    print("\nSample of entries to be deleted:")
    for i, entry in enumerate(entries[:10]):
        title = entry.get('title', '')[:80]
        print(f"  {entry['id']}: {title}")
    
    if len(entries) > 10:
        print(f"  ... and {len(entries) - 10} more")
    
    print(f"\nThese {len(entries)} entries will be deactivated because:")
    print("- Department is too generic ('Stanford Research')")
    print("- Most appear to be navigation elements, forms, or administrative pages")
    print("- They don't represent specific research opportunities")
    
    # Ask for confirmation
    confirm = input(f"\nProceed with deactivating all {len(entries)} 'Stanford Research' entries? (yes/no): ").lower().strip()
    
    if confirm not in ['yes', 'y']:
        print("Operation cancelled.")
        return
    
    # Extract IDs for bulk deletion
    ids_to_delete = [entry['id'] for entry in entries]
    
    try:
        # Use bulk deactivate endpoint
        response = requests.post(
            f"{API_BASE_URL}/admin/bulk-deactivate",
            json=ids_to_delete
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"\n✅ Successfully deactivated {len(ids_to_delete)} 'Stanford Research' entries")
        print(f"API response: {result}")
        
        # Get updated stats
        stats_response = requests.get(f"{API_BASE_URL}/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"\nUpdated database statistics:")
            print(f"  Active opportunities: {stats['active_opportunities']}")
            print(f"  Inactive opportunities: {stats['inactive_opportunities']}")
            print(f"  Total opportunities: {stats['total_opportunities']}")
        
    except requests.RequestException as e:
        print(f"❌ Error during bulk deletion: {e}")
        return

if __name__ == "__main__":
    main() 