#!/usr/bin/env python3
"""
Stanford Research Opportunities API - CDK App
Main entry point for AWS CDK deployment
"""

import os
import aws_cdk as cdk
from stacks.api_stack_simple import StanfordResearchApiStack


def main():
    """Initialize and deploy the Stanford Research API stack."""
    app = cdk.App()
    
    # Get deployment stage from environment or default to 'dev'
    stage = os.getenv("STAGE", "dev")
    
    # Create the API stack
    api_stack = StanfordResearchApiStack(
        app, 
        f"StanfordResearchApi-{stage}",
        stage=stage,
        env=cdk.Environment(
            account=os.getenv('CDK_DEFAULT_ACCOUNT'),
            region=os.getenv('CDK_DEFAULT_REGION', 'us-west-2')
        ),
        description=f"Stanford Research Opportunities API - {stage} environment"
    )
    
    # Add tags to all resources
    cdk.Tags.of(api_stack).add("Project", "StanfordResearchOpportunities")
    cdk.Tags.of(api_stack).add("Environment", stage)
    cdk.Tags.of(api_stack).add("ManagedBy", "CDK")
    
    app.synth()


if __name__ == "__main__":
    main()
