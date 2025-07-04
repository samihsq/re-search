#!/usr/bin/env python3
"""
Test script for LLM integration with scraping system.
Run this to verify that the Perplexity integration is working correctly.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

from app.config import settings
from app.services.llm_validation_service import llm_validation_service


async def test_llm_validation():
    """Test the LLM validation service with sample data."""
    
    # Sample opportunity data (similar to what scrapers would produce)
    sample_opportunity = {
        "title": "Environment and Policy Internships (EPIC)",
        "description": "Pursue environment, sustainability, and policy internships with leading not-for-profit organizations, and state and municipal agencies in California, nationwide, and internationally. Since 2017, the Stanford Environmental Program has connected over 200 students with meaningful summer internships.",
        "department": "Environment & Sustainability", 
        "opportunity_type": "internship",
        "funding_amount": "$8,000",
        "source_url": "https://solo.stanford.edu/programs/environment-and-policy-internships-epic",
        "deadline": "2025-01-15",
        "tags": ["sustainability", "environment", "internship", "summer"]
    }
    
    print("🧪 Testing LLM Validation Service...")
    print(f"🔧 Perplexity API Key configured: {'✅' if settings.perplexity_api_key else '❌'}")
    print(f"🔧 LLM Validation enabled: {'✅' if settings.enable_llm_validation else '❌'}")
    print()
    
    if not settings.perplexity_api_key:
        print("❌ PERPLEXITY_API_KEY not set in environment variables")
        print("   Please set PERPLEXITY_API_KEY to test LLM integration")
        return False
    
    try:
        print("📝 Testing with sample opportunity:")
        print(f"   Title: {sample_opportunity['title']}")
        print(f"   Department: {sample_opportunity['department']}")
        print(f"   Type: {sample_opportunity['opportunity_type']}")
        print()
        
        # Test the full LLM processing pipeline
        print("🔍 Starting LLM validation and enhancement...")
        
        async with llm_validation_service as llm_service:
            processed_opportunity, should_keep = await llm_service.process_opportunity(
                sample_opportunity, 
                sample_opportunity['source_url']
            )
        
        print("✅ LLM processing completed successfully!")
        print()
        print("📊 Results:")
        print(f"   Should keep: {'✅' if should_keep else '❌'}")
        print(f"   LLM Validated: {processed_opportunity.get('llm_validated', False)}")
        print(f"   Validation Score: {processed_opportunity.get('validation_score', 'N/A')}")
        print(f"   Enhancement Score: {processed_opportunity.get('enhancement_score', 'N/A')}")
        print(f"   Validation Reason: {processed_opportunity.get('validation_reason', 'N/A')}")
        print()
        
        if processed_opportunity.get('enhanced_description'):
            print("📝 Enhanced Description (first 200 chars):")
            print(f"   {processed_opportunity['enhanced_description'][:200]}...")
            print()
        
        if processed_opportunity.get('key_benefits'):
            print("🎯 Key Benefits:")
            for benefit in processed_opportunity.get('key_benefits', []):
                print(f"   • {benefit}")
            print()
            
        if processed_opportunity.get('target_audience'):
            print("👥 Target Audience:")
            for audience in processed_opportunity.get('target_audience', []):
                print(f"   • {audience}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error during LLM testing: {e}")
        return False


async def test_batch_processing():
    """Test batch processing with multiple opportunities."""
    
    sample_opportunities = [
        {
            "title": "CURIS Computer Science Research Program",
            "description": "The Computer Science Undergraduate Research Internship (CURIS) provides undergraduate students with an opportunity to conduct research with Stanford CS faculty members.",
            "department": "Computer Science",
            "opportunity_type": "research",
            "source_url": "https://curis.stanford.edu/"
        },
        {
            "title": "Bio-X Undergraduate Research Program", 
            "description": "The Bio-X Undergraduate Research Program (USRP) provides funding for undergraduates to conduct interdisciplinary research in the life sciences.",
            "department": "Biology",
            "opportunity_type": "funding",
            "funding_amount": "$6,000",
            "source_url": "https://biox.stanford.edu/research/undergraduate-research"
        }
    ]
    
    print("\n🧪 Testing Batch Processing...")
    print(f"📊 Processing {len(sample_opportunities)} opportunities")
    
    try:
        async with llm_validation_service as llm_service:
            processed_opportunities = await llm_service.process_opportunities_batch(
                sample_opportunities,
                "https://test.stanford.edu"
            )
        
        print(f"✅ Batch processing completed: {len(processed_opportunities)}/{len(sample_opportunities)} kept")
        
        for i, opp in enumerate(processed_opportunities):
            print(f"   {i+1}. {opp.get('title', 'Unknown')} - Score: {opp.get('validation_score', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during batch testing: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 Stanford Research Opportunities - LLM Integration Test")
    print("=" * 60)
    
    # Test individual processing
    success1 = await test_llm_validation()
    
    # Test batch processing  
    success2 = await test_batch_processing()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 All LLM integration tests passed!")
        print("🔧 Your system is ready to use LLM-enhanced scraping")
    else:
        print("❌ Some tests failed - check your configuration")
        
    print("\n💡 Tips:")
    print("   - Set PERPLEXITY_API_KEY in your environment")
    print("   - Set ENABLE_LLM_VALIDATION=true to enable validation")
    print("   - Monitor logs during scraping for LLM processing details")


if __name__ == "__main__":
    asyncio.run(main()) 