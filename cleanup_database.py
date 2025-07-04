#!/usr/bin/env python3
"""
Database Cleanup Script for Research Opportunities
Removes useless entries that don't represent actual opportunities.
"""

import requests
import json
import re
from typing import List, Dict, Set
from dataclasses import dataclass

# Configuration
API_BASE_URL = "http://localhost:8000/api/opportunities"

@dataclass
class CleanupStats:
    total_before: int = 0
    total_checked: int = 0
    marked_for_deletion: int = 0
    deleted: int = 0
    deletion_failures: int = 0

class OpportunityCleanup:
    def __init__(self):
        self.stats = CleanupStats()
        self.useless_ids = set()
        
        # Define patterns for useless entries
        self.useless_title_patterns = [
            # Generic/vague titles
            r'^research$',
            r'^admissions$',
            r'^department$',
            r'^department\s+\w+$',  # "Department Something"
            r'^program$',
            r'^programs$',
            r'^website$',
            r'^home$',
            r'^about$',
            r'^contact$',
            r'^overview$',
            r'^information$',
            r'^details$',
            
            # Navigation/menu items
            r'toggle\s+',
            r'^browse\s+',
            r'^\s*browse\s*$',
            r'menu',
            r'navigation',
            
            # Form/administrative entries
            r'application\s+form\s*$',
            r'application\s+form\s*-',
            r'-\s*application\s+form\s*$',
            r'^forms?$',
            r'^form\s+',
            r'^\s*form\s*$',
            
            # Website/link entries
            r'^program\s+website$',
            r'^website\s*-',
            r'-\s*website$',
            r'^link\s+to',
            r'^visit\s+',
            r'^see\s+',
            r'^click\s+',
            
            # Policy/procedural text (starts like sentences)
            r'^the\s+deadline\s+for',
            r'^students\s+who\s+',
            r'^students\s+must\s+',
            r'^additional\s+elective:',
            r'^requirements:',
            r'^note:',
            r'^please\s+',
            r'^all\s+students\s+',
            
            # Generic department/school listings
            r'^school\s+of\s+\w+toggle',
            r'toggle\s+school\s+of',
            
            # Very short non-descriptive titles
            r'^\w{1,3}$',  # 1-3 character titles
            
            # Error/broken entries
            r'\.{3,}',  # Multiple dots indicating truncation
            r'^error',
            r'^404',
            r'^page\s+not\s+found',
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.useless_title_patterns]
        
        # Additional filters for descriptions and other fields
        self.useless_description_patterns = [
            r'^$',  # Empty descriptions
            r'^\s*$',  # Whitespace only
            r'^click\s+here',
            r'^visit\s+the\s+website',
            r'^see\s+the\s+website',
            r'^more\s+information',
            r'^for\s+more\s+information',
            r'^application\s+available',
        ]

    def get_all_opportunities(self) -> List[Dict]:
        """Fetch all opportunities from the API."""
        print("Fetching all opportunities from database...")
        
        all_opportunities = []
        skip = 0
        limit = 1000
        
        while True:
            try:
                response = requests.get(
                    f"{API_BASE_URL}/",
                    params={"skip": skip, "limit": limit, "is_active": True}
                )
                response.raise_for_status()
                
                batch = response.json()
                if not batch:
                    break
                    
                all_opportunities.extend(batch)
                
                if len(batch) < limit:
                    break
                    
                skip += limit
                
            except requests.RequestException as e:
                print(f"Error fetching opportunities: {e}")
                break
        
        self.stats.total_before = len(all_opportunities)
        print(f"Fetched {len(all_opportunities)} total opportunities")
        return all_opportunities

    def is_useless_opportunity(self, opp: Dict) -> bool:
        """Determine if an opportunity should be considered useless."""
        title = (opp.get('title') or '').strip()
        description = (opp.get('description') or '').strip()
        
        if not title:
            return True
        
        # Check title patterns
        for pattern in self.compiled_patterns:
            if pattern.match(title):
                return True
        
        # Check for overly long titles that seem like navigation text
        if len(title) > 200:
            return True
        
        # Check for titles that are just department names
        if self._is_just_department_name(title):
            return True
        
        # Check for titles that are clearly navigation elements
        if self._is_navigation_element(title):
            return True
        
        # Check for broken/malformed titles
        if self._is_malformed_title(title):
            return True
        
        # Check description patterns
        if description and self._is_useless_description(description):
            return True
        
        return False

    def _is_just_department_name(self, title: str) -> bool:
        """Check if title is just a department name without program info."""
        # Common department patterns
        dept_patterns = [
            r'^(department\s+of\s+)?\w+\s+(department|school|college|institute)$',
            r'^(school|college)\s+of\s+\w+$',
            r'^\w+\s+department$',
            r'^biomedical\s+informatics$',
            r'^health\s+and\s+human\s+performance$',
            r'^\w+\s+lab$',  # Generic "Something Lab"
        ]
        
        for pattern in dept_patterns:
            if re.match(pattern, title, re.IGNORECASE):
                return True
        return False

    def _is_navigation_element(self, title: str) -> bool:
        """Check if title appears to be a navigation element."""
        nav_patterns = [
            r'current\s+students',
            r'prospective\s+students',
            r'fellowships\s+and\s+funding',
            r'guide\s+on\s+getting\s+into',
            r'how\s+your\s+application\s+is\s+reviewed',
            r'message\s+from\s+dean',
            r'self-assessment',
        ]
        
        for pattern in nav_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return True
        return False

    def _is_malformed_title(self, title: str) -> bool:
        """Check if title appears malformed or broken."""
        # Contains HTML elements
        if re.search(r'<[^>]+>', title):
            return True
        
        # Contains excessive capitalization or weird formatting
        if re.search(r'[A-Z]{5,}', title) and 'REU' not in title and 'NSF' not in title:
            return True
        
        # Contains navigation artifacts
        if re.search(r'(toggle|dropdown|menu|nav)', title, re.IGNORECASE):
            return True
        
        # Contains URL fragments
        if re.search(r'(https?://|www\.|\.(com|org|edu))', title):
            return True
        
        return False

    def _is_useless_description(self, description: str) -> bool:
        """Check if description is useless."""
        if len(description.strip()) < 10:
            return True
        
        for pattern in self.useless_description_patterns:
            if re.match(pattern, description.strip(), re.IGNORECASE):
                return True
        
        return False

    def analyze_opportunities(self, opportunities: List[Dict]) -> None:
        """Analyze all opportunities and identify useless ones."""
        print("\nAnalyzing opportunities for cleanup...")
        
        useless_count = 0
        
        for opp in opportunities:
            self.stats.total_checked += 1
            
            if self.is_useless_opportunity(opp):
                self.useless_ids.add(opp['id'])
                useless_count += 1
                
                # Print details for manual review
                title = opp.get('title', '')[:100]
                print(f"USELESS - ID {opp['id']}: {title}")
        
        self.stats.marked_for_deletion = useless_count
        print(f"\nAnalysis complete:")
        print(f"  Total checked: {self.stats.total_checked}")
        print(f"  Marked for deletion: {self.stats.marked_for_deletion}")
        print(f"  Will keep: {self.stats.total_checked - self.stats.marked_for_deletion}")

    def delete_useless_opportunities(self, dry_run: bool = True) -> None:
        """Delete or simulate deletion of useless opportunities."""
        if not self.useless_ids:
            print("No opportunities marked for deletion.")
            return
        
        if dry_run:
            print(f"\n=== DRY RUN MODE ===")
            print(f"Would delete {len(self.useless_ids)} opportunities")
            print("To actually delete, run with dry_run=False")
            return
        
        print(f"\n=== DELETING {len(self.useless_ids)} OPPORTUNITIES ===")
        
        # Convert to list for batch deletion
        ids_to_delete = list(self.useless_ids)
        
        try:
            # Use bulk deactivate endpoint
            response = requests.post(
                f"{API_BASE_URL}/admin/bulk-deactivate",
                json=ids_to_delete
            )
            response.raise_for_status()
            
            result = response.json()
            self.stats.deleted = len(ids_to_delete)
            print(f"Successfully deactivated {self.stats.deleted} opportunities")
            print(f"API response: {result}")
            
        except requests.RequestException as e:
            print(f"Error during bulk deletion: {e}")
            self.stats.deletion_failures = len(ids_to_delete)

    def generate_report(self) -> str:
        """Generate a cleanup report."""
        report = f"""
=== DATABASE CLEANUP REPORT ===

Before Cleanup:
  Total opportunities: {self.stats.total_before}

Analysis:
  Opportunities checked: {self.stats.total_checked}
  Marked for deletion: {self.stats.marked_for_deletion}
  Percentage useless: {(self.stats.marked_for_deletion / self.stats.total_checked * 100):.1f}%

Cleanup Results:
  Successfully deleted: {self.stats.deleted}
  Deletion failures: {self.stats.deletion_failures}
  
After Cleanup:
  Remaining opportunities: {self.stats.total_before - self.stats.deleted}
  Data quality improvement: {(self.stats.deleted / self.stats.total_before * 100):.1f}% reduction

=== PATTERNS USED FOR CLEANUP ===

Title patterns that were considered useless:
- Generic terms: research, admissions, department, program, website
- Navigation elements: toggle, browse, menu
- Form entries: application form, forms
- Policy text: "The deadline for...", "Students who..."
- Department listings without specific programs
- Very short titles (1-3 characters)
- Malformed/broken titles with HTML or excessive caps
- Overly long navigation text (>200 characters)

Additional filters:
- Empty or very short descriptions
- Just department names without program details
- Navigation menu items
- URL fragments or HTML in titles
"""
        return report

def main():
    """Main execution function."""
    print("=== RESEARCH OPPORTUNITIES DATABASE CLEANUP ===")
    print("This script will identify and remove useless database entries.")
    print()
    
    cleanup = OpportunityCleanup()
    
    # Step 1: Fetch all opportunities
    opportunities = cleanup.get_all_opportunities()
    if not opportunities:
        print("No opportunities found. Exiting.")
        return
    
    # Step 2: Analyze and identify useless ones
    cleanup.analyze_opportunities(opportunities)
    
    # Step 3: Show what would be deleted (dry run)
    cleanup.delete_useless_opportunities(dry_run=True)
    
    # Step 4: Ask for confirmation
    if cleanup.useless_ids:
        print(f"\nReady to delete {len(cleanup.useless_ids)} useless opportunities.")
        confirm = input("Do you want to proceed with deletion? (yes/no): ").lower().strip()
        
        if confirm in ['yes', 'y']:
            cleanup.delete_useless_opportunities(dry_run=False)
        else:
            print("Deletion cancelled.")
    
    # Step 5: Generate report
    report = cleanup.generate_report()
    print(report)
    
    # Save report to file
    with open('cleanup_report.txt', 'w') as f:
        f.write(report)
    print("Report saved to cleanup_report.txt")

if __name__ == "__main__":
    main() 