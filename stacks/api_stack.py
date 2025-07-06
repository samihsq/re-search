import os
from typing import Any, Dict, List, Optional

from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_apigatewayv2 as apigw,
    aws_iam as iam,
    CfnOutput,
    BundlingOptions
)
from constructs import Construct

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()


class StanfordResearchApiStack(Stack):
    """CDK Stack for Stanford Research Opportunities API"""

    def __init__(self, scope: Construct, construct_id: str, stage: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.stage = stage
        
        # Create IAM role for Lambda
        lambda_role = self._create_lambda_role()
        
        # Create Lambda function
        api_lambda = self._create_lambda_function(lambda_role)
        
        # Create API Gateway
        api_gateway = self._create_api_gateway(api_lambda)
        
        # Create outputs
        self._create_outputs(api_gateway, api_lambda, lambda_role)

    def _create_lambda_role(self) -> iam.Role:
        """Create IAM role for Lambda function with necessary permissions."""
        role = iam.Role(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
            inline_policies={
                "CloudWatchLogs": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                                "logs:DescribeLogGroups",
                                "logs:DescribeLogStreams"
                            ],
                            resources=["arn:aws:logs:*:*:*"]
                        )
                    ]
                )
            }
        )
        
        print(f"✅ Created Lambda execution role: {role.role_name}")
        return role

    def _create_lambda_function(self, role: iam.Role) -> _lambda.Function:
        """Create Lambda function with FastAPI application."""
        
        # Environment variables from serverless.yml
        environment_vars = {
            "STAGE": self.stage,
            "DEBUG": "false",
            "ENABLE_LLM_PARSING": "true",
            "DISABLE_SELENIUM": "true"
        }
        
        # Add environment variables from actual environment if they exist
        env_vars_to_check = [
            "DATABASE_URL",
            "REDIS_URL", 
            "GEMINI_API_KEY",
            "SCRAPING_API_KEY"
        ]
        
        for env_var in env_vars_to_check:
            if os.getenv(env_var):
                environment_vars[env_var] = os.getenv(env_var)
                print(f"✅ Added environment variable: {env_var}")
            else:
                print(f"⚠️  Environment variable not found: {env_var}")
                # Add reminder for database connectivity
                if env_var == "DATABASE_URL":
                    print("💡 To connect to your database, set DATABASE_URL in your .env file")
                    print("   Example: DATABASE_URL=postgresql://user:pass@host:5432/dbname")
        
        print(f"📋 Lambda function environment: {list(environment_vars.keys())}")
        
        # Create the Lambda function with database connectivity
        lambda_function = _lambda.Function(
            self,
            "ApiFunctionV2",  # Changed ID to force recreation
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="lambda_handler_database.handler",  # Changed to database-aware handler
            code=_lambda.Code.from_asset(
                "lambda_package",
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_9.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install --no-cache-dir -r lambda_requirements.txt -t /asset-output && "
                        "cp -r . /asset-output/ && "
                        "echo 'Lambda bundling completed successfully'"
                    ]
                )
            ),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "STAGE": self.stage,
                "DATABASE_URL": os.getenv("DATABASE_URL", ""),
                "REDIS_URL": os.getenv("REDIS_URL", ""),
                "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
                "SECRET_KEY": os.getenv("SECRET_KEY", ""),
                "DEBUG": os.getenv("DEBUG", "false"),
                "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
                "ENABLE_LLM_PARSING": os.getenv("ENABLE_LLM_PARSING", "false"),
                "DEPLOY_TIMESTAMP": "2025-07-06T07:00:00Z"
            }
        )
        
        print(f"✅ Created Lambda function: {lambda_function.function_name}")
        print(f"📋 Function ARN: {lambda_function.function_arn}")
        return lambda_function

    def _create_api_gateway(self, lambda_function: _lambda.Function) -> apigw.CfnApi:
        """Create API Gateway HTTP API with CORS configuration."""
        
        # Create HTTP API
        api = apigw.CfnApi(
            self, "ResearchOpportunitiesApi",
            name=f"stanford-research-opportunities-{self.stage}",
            description=f"Stanford Research Opportunities API - {self.stage}",
            protocol_type="HTTP",
            cors_configuration=apigw.CfnApi.CorsProperty(
                allow_origins=[
                    "https://samih1435.github.io",
                    "http://localhost:3000", 
                    "https://localhost:3000"
                ],
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "X-Amz-Date",
                    "X-Api-Key",
                    "X-Amz-Security-Token"
                ],
                allow_methods=[
                    "GET",
                    "POST",
                    "PUT",
                    "DELETE",
                    "OPTIONS"
                ],
                allow_credentials=False
            )
        )
        
        # Create Lambda integration
        lambda_integration = apigw.CfnIntegration(
            self, "LambdaIntegration",
            api_id=api.ref,
            integration_type="AWS_PROXY",
            integration_uri=lambda_function.function_arn,
            payload_format_version="2.0"
        )
        
        # Create routes
        proxy_route = apigw.CfnRoute(
            self, "ProxyRoute",
            api_id=api.ref,
            route_key="ANY /{proxy+}",
            target=f"integrations/{lambda_integration.ref}"
        )
        
        root_route = apigw.CfnRoute(
            self, "RootRoute",
            api_id=api.ref,
            route_key="ANY /",
            target=f"integrations/{lambda_integration.ref}"
        )
        
        # Create stage
        stage = apigw.CfnStage(
            self, "ApiStage",
            api_id=api.ref,
            stage_name="$default",
            auto_deploy=True,
            description=f"Default stage for {self.stage} environment"
        )
        
        # Grant API Gateway permission to invoke Lambda
        lambda_function.add_permission(
            "ApiGatewayInvoke",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:execute-api:{self.region}:{self.account}:{api.ref}/*/*"
        )
        
        print(f"✅ Created API Gateway: {api.ref}")
        print(f"📋 API URL: https://{api.ref}.execute-api.{self.region}.amazonaws.com/")
        return api

    def _create_outputs(self, api_gateway: apigw.CfnApi, lambda_function: _lambda.Function, lambda_role: iam.Role) -> None:
        """Create CloudFormation outputs."""
        
        # Main outputs
        CfnOutput(
            self, "ApiUrl",
            value=f"https://{api_gateway.ref}.execute-api.{self.region}.amazonaws.com/",
            description="API Gateway URL",
            export_name=f"stanford-research-api-url-{self.stage}"
        )
        
        CfnOutput(
            self, "ApiId", 
            value=api_gateway.ref,
            description="API Gateway ID",
            export_name=f"stanford-research-api-id-{self.stage}"
        )
        
        # Additional detailed outputs
        CfnOutput(
            self, "LambdaFunctionName",
            value=lambda_function.function_name,
            description="Lambda Function Name",
            export_name=f"stanford-research-api-function-name-{self.stage}"
        )
        
        CfnOutput(
            self, "LambdaFunctionArn",
            value=lambda_function.function_arn,
            description="Lambda Function ARN",
            export_name=f"stanford-research-api-function-arn-{self.stage}"
        )
        
        CfnOutput(
            self, "LambdaRoleArn",
            value=lambda_role.role_arn,
            description="Lambda Execution Role ARN",
            export_name=f"stanford-research-api-role-arn-{self.stage}"
        )
        
        CfnOutput(
            self, "LambdaLogGroup",
            value=f"/aws/lambda/{lambda_function.function_name}",
            description="Lambda Function Log Group",
            export_name=f"stanford-research-api-log-group-{self.stage}"
        )
        
        CfnOutput(
            self, "DeploymentStage",
            value=self.stage,
            description="Deployment Stage",
            export_name=f"stanford-research-api-stage-{self.stage}"
        )
        
        CfnOutput(
            self, "StackName",
            value=self.stack_name,
            description="CloudFormation Stack Name",
            export_name=f"stanford-research-api-stack-name-{self.stage}"
        )
        
        # Health check and testing URLs
        api_url = f"https://{api_gateway.ref}.execute-api.{self.region}.amazonaws.com/"
        
        CfnOutput(
            self, "HealthCheckUrl",
            value=f"{api_url}health",
            description="Health Check Endpoint",
            export_name=f"stanford-research-api-health-url-{self.stage}"
        )
        
        CfnOutput(
            self, "OpportunitiesUrl",
            value=f"{api_url}api/opportunities",
            description="Opportunities API Endpoint",
            export_name=f"stanford-research-api-opportunities-url-{self.stage}"
        )
        
        # Useful commands for monitoring
        CfnOutput(
            self, "ViewLogsCommand",
            value=f"aws logs tail /aws/lambda/{lambda_function.function_name} --follow",
            description="Command to view Lambda logs",
            export_name=f"stanford-research-api-logs-command-{self.stage}"
        )
        
        CfnOutput(
            self, "TestCommand",
            value=f"curl -v {api_url}health",
            description="Command to test API health",
            export_name=f"stanford-research-api-test-command-{self.stage}"
        )
        
        print(f"✅ Created {12} CloudFormation outputs")
        print(f"📋 API URL: {api_url}")
        print(f"📋 Health Check: {api_url}health")
        print(f"📋 Opportunities API: {api_url}api/opportunities") 