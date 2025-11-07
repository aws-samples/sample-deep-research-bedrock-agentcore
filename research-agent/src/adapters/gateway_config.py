"""
Gateway configuration loader
Loads Gateway URL from SSM Parameter Store at runtime

Configuration Path:
  /{PROJECT_NAME}/tools/gateway/url
  /{PROJECT_NAME}/tools/config/region

Environment Variables Required:
  - PROJECT_NAME: Project name (default: deep-research-agent)
  - AWS_REGION: AWS region for SSM client (default: us-west-2)
"""
import os
import json
import time
import boto3
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Cache configuration to avoid repeated SSM calls
_gateway_config_cache: Optional[Dict[str, str]] = None
_cache_timestamp: Optional[float] = None
CACHE_TTL = 300  # 5 minutes


def load_gateway_config(force_refresh: bool = False) -> Dict[str, str]:
    """
    Load Gateway configuration with caching

    Priority:
      1. Environment variable GATEWAY_URL (for override/testing)
      2. SSM Parameter Store runtime lookup (production)
      3. Local config file gateway_config.json (development)

    Args:
        force_refresh: Force refresh cache by re-reading from SSM

    Returns:
        Dict with gateway_url, region, auth_mode

    Raises:
        ValueError: If no configuration found
    """
    global _gateway_config_cache, _cache_timestamp

    # Check cache (unless force_refresh)
    if not force_refresh and _gateway_config_cache and _cache_timestamp:
        if time.time() - _cache_timestamp < CACHE_TTL:
            logger.debug("✅ Using cached Gateway config")
            return _gateway_config_cache

    # Priority 1: Environment variable (for testing/override)
    if 'GATEWAY_URL' in os.environ:
        config = {
            'gateway_url': os.environ['GATEWAY_URL'],
            'region': os.environ.get('AWS_REGION', 'us-west-2'),
            'auth_mode': 'IAM'
        }
        logger.info("✅ Loaded Gateway config from GATEWAY_URL environment variable")
        _gateway_config_cache = config
        _cache_timestamp = time.time()
        return config

    # Priority 2: SSM Parameter Store (production)
    try:
        config = _load_from_ssm()
        _gateway_config_cache = config
        _cache_timestamp = time.time()
        return config
    except Exception as e:
        logger.warning(f"Could not load from SSM Parameter Store: {e}")

    # Priority 3: Local config file (development)
    config_paths = [
        'gateway_config.json',
        '/app/gateway_config.json',
        os.path.join(os.path.dirname(__file__), '../../gateway_config.json')
    ]

    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    config = json.load(f)
                    logger.info(f"✅ Loaded Gateway config from {path}")
                    _gateway_config_cache = config
                    _cache_timestamp = time.time()
                    return config
            except Exception as e:
                logger.warning(f"Failed to load config from {path}: {e}")

    # No configuration found
    raise ValueError(
        "No Gateway configuration found. Please ensure:\n"
        "  1. Tools are deployed: terraform/deploy-tools.sh\n"
        "  2. SSM parameters exist at: /{PROJECT_NAME}/tools/gateway/url\n"
        "  3. Or set GATEWAY_URL environment variable\n"
        "  4. Or provide gateway_config.json for local development"
    )


def _load_from_ssm() -> Dict[str, str]:
    """
    Load Gateway configuration from SSM Parameter Store

    SSM Path Format:
      /{project_name}/tools/gateway/url
      /{project_name}/tools/config/region

    Returns:
        Dict with gateway_url, region, auth_mode

    Raises:
        Exception: If parameters not found or SSM access fails
    """
    # Get configuration from environment
    region = os.environ.get('AWS_REGION', 'us-west-2')
    project_name = os.environ.get('PROJECT_NAME', 'deep-research-agent')

    logger.info(f"🔍 Loading Gateway config from SSM Parameter Store")
    logger.info(f"   Project: {project_name}")
    logger.info(f"   Region: {region}")

    # Create SSM client
    ssm = boto3.client('ssm', region_name=region)

    # Build parameter paths
    gateway_url_path = f'/{project_name}/tools/gateway/url'
    gateway_region_path = f'/{project_name}/tools/config/region'

    logger.debug(f"   Gateway URL path: {gateway_url_path}")
    logger.debug(f"   Gateway region path: {gateway_region_path}")

    try:
        # Get gateway URL (required)
        gateway_url_response = ssm.get_parameter(Name=gateway_url_path)
        gateway_url = gateway_url_response['Parameter']['Value']
        logger.info(f"✅ Found Gateway URL: {gateway_url}")

        # Get gateway region (optional, fallback to current region)
        try:
            gateway_region_response = ssm.get_parameter(Name=gateway_region_path)
            gateway_region = gateway_region_response['Parameter']['Value']
            logger.info(f"✅ Found Gateway region: {gateway_region}")
        except ssm.exceptions.ParameterNotFound:
            gateway_region = region
            logger.debug(f"Gateway region parameter not found, using current region: {gateway_region}")

        config = {
            'gateway_url': gateway_url,
            'region': gateway_region,
            'auth_mode': 'IAM'
        }

        logger.info("✅ Successfully loaded Gateway config from SSM Parameter Store")
        return config

    except ssm.exceptions.ParameterNotFound as e:
        logger.error(f"❌ Gateway configuration not found in SSM: {e}")
        logger.error(f"   Expected path: {gateway_url_path}")
        logger.error(f"   Please ensure Tools are deployed (terraform/deploy-tools.sh)")
        raise ValueError(f"Gateway URL parameter not found: {gateway_url_path}")

    except Exception as e:
        logger.error(f"❌ Failed to load Gateway config from SSM: {e}")
        raise


def get_gateway_url() -> str:
    """Get Gateway URL from config"""
    return load_gateway_config()['gateway_url']


def get_gateway_region() -> str:
    """Get Gateway region from config"""
    return load_gateway_config().get('region', 'us-west-2')


def clear_cache():
    """Clear configuration cache (useful for testing)"""
    global _gateway_config_cache, _cache_timestamp
    _gateway_config_cache = None
    _cache_timestamp = None
    logger.debug("Configuration cache cleared")
