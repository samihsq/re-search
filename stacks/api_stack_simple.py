import os
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigw,
    aws_iam as iam,
    CfnOutput,
    BundlingOptions
)
from constructs import Construct


class StanfordResearchApiStack(Stack):
    """CDK Stack for Stanford Research Opportunities API"""

    def __init__(self, scope: Construct, construct_id: str, stage: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.stage = stage
        
        # Create Lambda function
        api_lambda = self._create_lambda_function()
        
        # Create API Gateway
        api_gateway = self._create_api_gateway(api_lambda)
        
        # Create outputs
        self._create_outputs(api_gateway, api_lambda)

    def _create_lambda_function(self) -> _lambda.Function:
        """Create Lambda function with FastAPI application."""
        
        # Create the Lambda function
        lambda_function = _lambda.Function(
            self,
            "ApiFunctionV3",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="lambda_handler.handler",
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
                "DEBUG": "false",
                "LOG_LEVEL": "INFO",
                "ENABLE_LLM_PARSING": "true"
            }
        )
        
        print(f"✅ Created Lambda function: {lambda_function.function_name}")
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
                allow_origins=["*"],
                allow_headers=["Content-Type", "Authorization"],
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
            auto_deploy=True
        )
        
        # Grant API Gateway permission to invoke Lambda
        lambda_function.add_permission(
            "ApiGatewayInvoke",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:execute-api:{self.region}:{self.account}:{api.ref}/*/*"
        )
        
        print(f"✅ Created API Gateway: {api.ref}")
        return api

    def _create_outputs(self, api_gateway: apigw.CfnApi, lambda_function: _lambda.Function) -> None:
        """Create CloudFormation outputs."""
        
        api_url = f"https://{api_gateway.ref}.execute-api.{self.region}.amazonaws.com/"
        
        CfnOutput(
            self, "ApiUrl",
            value=api_url,
            description="API Gateway URL"
        )
        
        CfnOutput(
            self, "HealthCheckUrl",
            value=f"{api_url}health",
            description="Health Check Endpoint"
        )
        
        CfnOutput(
            self, "OpportunitiesUrl",
            value=f"{api_url}api/opportunities",
            description="Opportunities API Endpoint"
        )
        
        print(f"✅ API URL: {api_url}")
        print(f"✅ Health Check: {api_url}health")
        print(f"✅ Opportunities API: {api_url}api/opportunities") 