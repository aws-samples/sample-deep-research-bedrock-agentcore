"""
Gateway Authentication Utilities

Provides AWS SigV4 authentication for AgentCore Gateway connections.
Supports both MCP client and direct HTTP requests.
"""

import boto3
import httpx
from typing import Generator, Optional
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials


class SigV4HTTPXAuth(httpx.Auth):
    """
    HTTPX Auth class that signs requests with AWS SigV4.

    Used for authenticating with AWS services that require IAM authentication,
    such as AgentCore Gateway.
    """

    def __init__(
        self,
        credentials: Optional[Credentials] = None,
        service: str = "bedrock-agentcore",
        region: Optional[str] = None,
    ):
        """
        Initialize SigV4 authentication.

        Args:
            credentials: AWS credentials. If None, uses boto3 session credentials.
            service: AWS service name (default: 'bedrock-agentcore')
            region: AWS region. If None, uses default region from boto3 session.
        """
        # Get credentials from boto3 session if not provided
        if credentials is None:
            session = boto3.Session()
            credentials = session.get_credentials()
            if credentials is None:
                raise ValueError("No AWS credentials found. Configure AWS credentials.")

        # Get region from boto3 session if not provided
        if region is None:
            session = boto3.Session()
            region = session.region_name
            if region is None:
                raise ValueError("No AWS region found. Set AWS_REGION or configure AWS region.")

        self.credentials = credentials
        self.service = service
        self.region = region
        self.signer = SigV4Auth(credentials, service, region)

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        """
        Signs the request with SigV4 and adds the signature to the request headers.

        This method is called by httpx for each request.
        """
        # Create an AWS request
        headers = dict(request.headers)

        # Remove 'connection' header - it's not used in calculating the request
        # signature on the server-side, and results in a signature mismatch if included
        headers.pop("connection", None)

        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers=headers,
        )

        # Sign the request with SigV4
        self.signer.add_auth(aws_request)

        # Add the signature header to the original request
        request.headers.update(dict(aws_request.headers))

        yield request


def get_sigv4_auth(
    service: str = "bedrock-agentcore",
    region: Optional[str] = None,
    credentials: Optional[Credentials] = None,
) -> SigV4HTTPXAuth:
    """
    Get a SigV4 auth handler for httpx requests.

    Args:
        service: AWS service name (default: 'bedrock-agentcore')
        region: AWS region. If None, uses default region from boto3 session.
        credentials: AWS credentials. If None, uses boto3 session credentials.

    Returns:
        SigV4HTTPXAuth instance for use with httpx clients

    Example:
        >>> auth = get_sigv4_auth()
        >>> async with httpx.AsyncClient(auth=auth) as client:
        ...     response = await client.get(gateway_url)
    """
    return SigV4HTTPXAuth(
        credentials=credentials,
        service=service,
        region=region,
    )


def get_gateway_region_from_url(gateway_url: str) -> str:
    """
    Extract AWS region from Gateway URL.

    Gateway URLs follow this pattern:
    https://gateway-xxx.execute-api.{region}.amazonaws.com/...

    Args:
        gateway_url: AgentCore Gateway URL

    Returns:
        AWS region (e.g., 'us-west-2')

    Raises:
        ValueError: If region cannot be extracted from URL
    """
    import re

    # Pattern for extracting region from Gateway URL
    # Format: https://...bedrock-agentcore.{region}.amazonaws.com
    pattern = r'bedrock-agentcore\.([a-z0-9-]+)\.amazonaws\.com'
    match = re.search(pattern, gateway_url)

    if match:
        return match.group(1)

    # Fallback: try API Gateway pattern
    pattern = r'execute-api\.([a-z0-9-]+)\.amazonaws\.com'
    match = re.search(pattern, gateway_url)

    if match:
        return match.group(1)

    # If we can't extract region, use default from boto3
    session = boto3.Session()
    region = session.region_name

    if region is None:
        raise ValueError(
            f"Cannot extract region from URL: {gateway_url}\n"
            "Please set AWS_REGION environment variable or configure AWS region."
        )

    return region


def create_authenticated_httpx_client(
    gateway_url: str,
    service: str = "bedrock-agentcore",
    region: Optional[str] = None,
    credentials: Optional[Credentials] = None,
    **httpx_kwargs,
) -> httpx.AsyncClient:
    """
    Create an httpx AsyncClient with SigV4 authentication.

    Args:
        gateway_url: AgentCore Gateway URL
        service: AWS service name (default: 'bedrock-agentcore')
        region: AWS region. If None, extracts from gateway_url or uses default.
        credentials: AWS credentials. If None, uses boto3 session credentials.
        **httpx_kwargs: Additional arguments to pass to httpx.AsyncClient

    Returns:
        httpx.AsyncClient configured with SigV4 authentication

    Example:
        >>> async with create_authenticated_httpx_client(gateway_url) as client:
        ...     response = await client.post(f"{gateway_url}/mcp", json=payload)
    """
    # Extract region from URL if not provided
    if region is None:
        region = get_gateway_region_from_url(gateway_url)

    # Get SigV4 auth
    auth = get_sigv4_auth(
        service=service,
        region=region,
        credentials=credentials,
    )

    # Create and return httpx client
    return httpx.AsyncClient(auth=auth, **httpx_kwargs)


if __name__ == '__main__':
    # Example usage
    import asyncio

    async def test_gateway_auth():
        gateway_url = "https://research-gateway-research-tools-xxx.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp"

        print("Testing SigV4 authentication...")
        print(f"Gateway URL: {gateway_url}")

        # Extract region
        region = get_gateway_region_from_url(gateway_url)
        print(f"Region: {region}")

        # Create authenticated client
        async with create_authenticated_httpx_client(gateway_url, region=region) as client:
            # Test request
            response = await client.get(gateway_url)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")

    asyncio.run(test_gateway_auth())
