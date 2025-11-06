"""
Configuration Loader for Research Agent

Loads configuration from AWS Parameter Store and Secrets Manager.
Falls back to .env file for local development.

Usage:
    from src.utils.config_loader import load_config

    config = load_config()

    # Access configuration
    memory_id = config['AGENTCORE_MEMORY_ID']
    dynamodb_table = config['DYNAMODB_STATUS_TABLE']
    tavily_key = config['TAVILY_API_KEY']
"""

import os
import json
import boto3
from typing import Dict, Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load configuration from AWS Parameter Store, Secrets Manager, and .env"""

    def __init__(self, project_name: str = "research-gateway", use_aws: bool = True):
        """
        Initialize configuration loader

        Args:
            project_name: Project name used in Parameter Store paths
            use_aws: If True, load from AWS services; if False, only use .env
        """
        self.project_name = project_name
        self.use_aws = use_aws
        self.config: Dict[str, str] = {}

        # Initialize AWS clients if needed
        if self.use_aws:
            try:
                self.ssm_client = boto3.client('ssm')
                self.secrets_client = boto3.client('secretsmanager')
                self.aws_available = True
            except Exception as e:
                logger.warning(f"AWS services not available: {e}. Falling back to .env")
                self.aws_available = False
        else:
            self.aws_available = False

    def load_from_env(self) -> Dict[str, str]:
        """Load configuration from .env file"""
        load_dotenv()

        config = {
            'AWS_REGION': os.getenv('AWS_REGION', 'us-west-2'),
            'AGENTCORE_MEMORY_ID': os.getenv('AGENTCORE_MEMORY_ID', ''),
            'DYNAMODB_STATUS_TABLE': os.getenv('DYNAMODB_STATUS_TABLE', ''),
            'S3_OUTPUTS_BUCKET': os.getenv('S3_OUTPUTS_BUCKET', ''),
            'TAVILY_API_KEY': os.getenv('TAVILY_API_KEY', ''),
            'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY', ''),
            'GOOGLE_SEARCH_ENGINE_ID': os.getenv('GOOGLE_SEARCH_ENGINE_ID', ''),
            'LANGCHAIN_API_KEY': os.getenv('LANGCHAIN_API_KEY', ''),
            'LANGCHAIN_TRACING_V2': os.getenv('LANGCHAIN_TRACING_V2', 'true'),
            'LANGCHAIN_PROJECT': os.getenv('LANGCHAIN_PROJECT', 'research-agent'),
        }

        return config

    def _get_parameter_store_value(self, parameter_name: str) -> Optional[str]:
        """Get value from Parameter Store"""
        try:
            response = self.ssm_client.get_parameter(
                Name=parameter_name,
                WithDecryption=True
            )
            return response['Parameter']['Value']
        except self.ssm_client.exceptions.ParameterNotFound:
            logger.warning(f"Parameter not found: {parameter_name}")
            return None
        except Exception as e:
            logger.error(f"Error getting parameter {parameter_name}: {e}")
            return None

    def _get_secret_value(self, secret_arn: str) -> Optional[Dict[str, str]]:
        """Get value from Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_arn)
            secret_string = response['SecretString']
            return json.loads(secret_string)
        except self.secrets_client.exceptions.ResourceNotFoundException:
            logger.warning(f"Secret not found: {secret_arn}")
            return None
        except Exception as e:
            logger.error(f"Error getting secret {secret_arn}: {e}")
            return None

    def _find_parameter_by_suffix(self, suffix: str) -> Optional[str]:
        """Find parameter by suffix (auto-detects suffix from existing parameters)"""
        try:
            # List all parameters with project prefix
            paginator = self.ssm_client.get_paginator('describe_parameters')

            for page in paginator.paginate(
                ParameterFilters=[
                    {
                        'Key': 'Name',
                        'Option': 'BeginsWith',
                        'Values': [f'/{self.project_name}/']
                    }
                ]
            ):
                for param in page['Parameters']:
                    param_name = param['Name']
                    # Extract suffix from first parameter
                    parts = param_name.split('/')
                    if len(parts) >= 3:
                        detected_suffix = parts[2]
                        # Try to get the requested parameter with this suffix
                        full_path = f"/{self.project_name}/{detected_suffix}/{suffix}"
                        value = self._get_parameter_store_value(full_path)
                        if value:
                            return value

            return None
        except Exception as e:
            logger.error(f"Error finding parameter by suffix {suffix}: {e}")
            return None

    def load_from_aws(self) -> Dict[str, str]:
        """Load configuration from AWS Parameter Store and Secrets Manager"""
        if not self.aws_available:
            return {}

        config = {}

        # Load from Parameter Store
        # Try to auto-detect suffix or use common patterns
        param_mappings = {
            'AGENTCORE_MEMORY_ID': 'agentcore/memory-id',
            'DYNAMODB_STATUS_TABLE': 'dynamodb/status-table',
            'S3_OUTPUTS_BUCKET': 's3/outputs-bucket',
            'AWS_REGION': 'config/region',
            'GATEWAY_URL': 'gateway/url',
            'LANGCHAIN_PROJECT': 'langchain/project',
            'LANGCHAIN_TRACING_V2': 'langchain/tracing-v2',
        }

        for config_key, param_suffix in param_mappings.items():
            value = self._find_parameter_by_suffix(param_suffix)
            if value:
                config[config_key] = value
                logger.info(f"Loaded {config_key} from Parameter Store")

        # Load from Secrets Manager
        # Note: Secret ARNs would need to be known or discovered
        # For now, we'll keep secrets in .env as they're already there

        return config

    def load_config(self) -> Dict[str, str]:
        """
        Load complete configuration

        Priority:
        1. AWS Parameter Store / Secrets Manager (if available)
        2. .env file (fallback and for local development)
        """
        # Start with .env (always available)
        config = self.load_from_env()

        # Override with AWS values if available
        if self.use_aws and self.aws_available:
            aws_config = self.load_from_aws()
            config.update(aws_config)
            logger.info("Configuration loaded from AWS services")
        else:
            logger.info("Configuration loaded from .env file")

        # Validate required fields
        required_fields = [
            'AGENTCORE_MEMORY_ID',
            'DYNAMODB_STATUS_TABLE',
            'S3_OUTPUTS_BUCKET',
            'TAVILY_API_KEY'
        ]

        missing_fields = [field for field in required_fields if not config.get(field)]
        if missing_fields:
            logger.warning(f"Missing required configuration: {', '.join(missing_fields)}")

        self.config = config
        return config

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get configuration value by key"""
        return self.config.get(key, default)

    def __getitem__(self, key: str) -> str:
        """Dictionary-style access"""
        return self.config[key]


# Global instance for easy access
_config_loader: Optional[ConfigLoader] = None


def load_config(force_reload: bool = False, use_aws: bool = True) -> Dict[str, str]:
    """
    Load configuration (singleton pattern)

    Args:
        force_reload: Force reload configuration
        use_aws: Load from AWS services (True) or only .env (False)

    Returns:
        Configuration dictionary
    """
    global _config_loader

    if _config_loader is None or force_reload:
        _config_loader = ConfigLoader(use_aws=use_aws)
        return _config_loader.load_config()

    return _config_loader.config


def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get configuration value by key

    Args:
        key: Configuration key
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    if _config_loader is None:
        load_config()

    return _config_loader.get(key, default)


if __name__ == '__main__':
    # Example usage
    logging.basicConfig(level=logging.INFO)

    print("Loading configuration...")
    config = load_config()

    print("\nConfiguration loaded:")
    for key, value in config.items():
        # Mask sensitive values
        if 'KEY' in key or 'SECRET' in key:
            masked_value = f"{value[:10]}..." if value else "(not set)"
            print(f"  {key}: {masked_value}")
        else:
            print(f"  {key}: {value}")
