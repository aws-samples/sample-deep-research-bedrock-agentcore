"""
Finance Lambda - Simplified version without numpy/pandas dependencies
Returns a message that finance tools are currently disabled
"""
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda handler that returns a disabled message
    """
    logger.info(f"Finance Lambda called with event: {json.dumps(event)}")

    return {
        "statusCode": 503,
        "body": json.dumps({
            "error": "Finance tools are currently disabled",
            "message": "Finance tools require numpy/pandas dependencies that are not compatible with the Lambda runtime. Consider using alternative data sources or Lambda Layers.",
            "available_alternatives": [
                "Use Alpha Vantage API",
                "Use IEX Cloud API",
                "Deploy as Lambda Container Image with custom runtime"
            ]
        })
    }
