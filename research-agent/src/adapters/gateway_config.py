"""
Gateway configuration loader
Supports multiple sources: file, Parameter Store, environment
"""
import os
import json
import boto3
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def load_gateway_config() -> Dict[str, str]:
    """
    Load Gateway configuration from available sources
    Priority: gateway_config.json > Parameter Store > Environment

    Returns:
        Dict with gateway_url, region, auth_mode

    Raises:
        ValueError: If no configuration found
    """
    # 1. Try local config file
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
                    return config
            except Exception as e:
                logger.warning(f"Failed to load config from {path}: {e}")

    # 2. Try Parameter Store (if deployed)
    try:
        ssm = boto3.client('ssm')

        # Try to get suffix from environment or find dynamically
        suffix = os.environ.get('RESOURCE_SUFFIX', '')

        if not suffix:
            # Try to find any gateway URL parameter
            try:
                response = ssm.get_parameters_by_path(
                    Path='/research-gateway/',
                    Recursive=True
                )
                for param in response.get('Parameters', []):
                    if 'gateway/url' in param['Name']:
                        gateway_url = param['Value']
                        # Extract suffix from parameter name if possible
                        # /research-gateway/{suffix}/gateway/url
                        parts = param['Name'].split('/')
                        if len(parts) >= 3:
                            suffix = parts[2]
                        break
            except Exception as e:
                logger.debug(f"Could not search parameters: {e}")

        # Build parameter names
        if suffix:
            prefix = f'/research-gateway/{suffix}'
        else:
            prefix = '/research-gateway'

        gateway_url_param = f'{prefix}/gateway/url'
        region_param = f'{prefix}/config/region'

        try:
            gateway_url = ssm.get_parameter(Name=gateway_url_param)['Parameter']['Value']
        except ssm.exceptions.ParameterNotFound:
            # Try without suffix
            gateway_url = ssm.get_parameter(Name='/research-gateway/gateway/url')['Parameter']['Value']

        try:
            region = ssm.get_parameter(Name=region_param)['Parameter']['Value']
        except:
            region = os.environ.get('AWS_REGION', 'us-west-2')

        config = {
            'gateway_url': gateway_url,
            'region': region,
            'auth_mode': 'IAM'
        }
        logger.info("✅ Loaded Gateway config from Parameter Store")
        return config

    except Exception as e:
        logger.warning(f"Could not load from Parameter Store: {e}")

    # 3. Try environment variables
    if 'GATEWAY_URL' in os.environ:
        config = {
            'gateway_url': os.environ['GATEWAY_URL'],
            'region': os.environ.get('AWS_REGION', 'us-west-2'),
            'auth_mode': 'IAM'
        }
        logger.info("✅ Loaded Gateway config from environment")
        return config

    raise ValueError(
        "No Gateway configuration found. Please provide one of:\n"
        "  1. gateway_config.json file\n"
        "  2. AWS Systems Manager Parameter Store parameters\n"
        "  3. GATEWAY_URL environment variable"
    )


def get_gateway_url() -> str:
    """Get Gateway URL from config"""
    return load_gateway_config()['gateway_url']


def get_gateway_region() -> str:
    """Get Gateway region from config"""
    return load_gateway_config().get('region', 'us-west-2')
