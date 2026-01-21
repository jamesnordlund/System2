#!/usr/bin/env python3
"""
AWS Bedrock Client for System2 Framework

Provides a unified interface for accessing Claude models through AWS Bedrock,
with authentication, error handling, and fallback capabilities.
"""

import boto3
import json
import os
import logging
from typing import Dict, Any, Optional, Union
from botocore.exceptions import ClientError, BotoCoreError
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BedrockClient:
    """
    AWS Bedrock client for System2 framework with authentication and model management.
    """
    
    def __init__(self, config_path: str = ".system2/config.yml"):
        """Initialize the Bedrock client with configuration."""
        self.config = self._load_config(config_path)
        self.bedrock_config = self.config.get("providers", {}).get("bedrock", {})
        
        # Initialize boto3 client
        self.client = None
        self._initialize_client()
        
        # Model mappings
        self.models = self.bedrock_config.get("models", {})
        self.default_model = self.bedrock_config.get("default_model", "claude-3-5-sonnet-20241022")
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load System2 configuration file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Configuration file {config_path} not found. Using defaults.")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration: {e}")
            return {}
    
    def _initialize_client(self):
        """Initialize the Bedrock runtime client with proper authentication."""
        try:
            region = self.bedrock_config.get("region", os.environ.get("AWS_DEFAULT_REGION", "us-west-2"))
            auth_config = self.bedrock_config.get("auth", {})
            
            # Session configuration
            session_kwargs = {"region_name": region}
            
            # Use profile if specified
            if auth_config.get("profile"):
                session_kwargs["profile_name"] = auth_config["profile"]
            
            session = boto3.Session(**session_kwargs)
            
            # Assume role if specified
            if auth_config.get("role_arn"):
                sts = session.client("sts")
                response = sts.assume_role(
                    RoleArn=auth_config["role_arn"],
                    RoleSessionName="System2BedrockAccess"
                )
                credentials = response["Credentials"]
                
                self.client = boto3.client(
                    "bedrock-runtime",
                    region_name=region,
                    aws_access_key_id=credentials["AccessKeyId"],
                    aws_secret_access_key=credentials["SecretAccessKey"],
                    aws_session_token=credentials["SessionToken"]
                )
            else:
                self.client = session.client("bedrock-runtime")
                
            logger.info("Bedrock client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Bedrock is available and properly configured."""
        if not self.client:
            return False
            
        try:
            # Test with a minimal request
            self.client.list_foundation_models()
            return True
        except Exception as e:
            logger.error(f"Bedrock availability check failed: {e}")
            return False
    
    def invoke_model(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Invoke a Claude model through Bedrock.
        
        Args:
            prompt: The input prompt
            model: Model identifier (defaults to configured default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model parameters
            
        Returns:
            Dictionary containing the response and metadata
        """
        if not self.client:
            raise RuntimeError("Bedrock client not initialized")
        
        # Use provided model or default
        model_id = model or self.default_model
        
        # Get defaults from config
        defaults = self.bedrock_config.get("defaults", {})
        
        # Prepare request body
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens or defaults.get("max_tokens", 4096),
            "temperature": temperature or defaults.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", defaults.get("top_p", 0.9))
        }
        
        try:
            # Make the request
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json"
            )
            
            # Parse response
            response_body = json.loads(response["body"].read())
            
            # Extract the generated text
            content = response_body.get("content", [])
            if content and len(content) > 0:
                generated_text = content[0].get("text", "")
            else:
                generated_text = ""
            
            # Calculate cost estimate (approximate)
            input_tokens = response_body.get("usage", {}).get("input_tokens", 0)
            output_tokens = response_body.get("usage", {}).get("output_tokens", 0)
            cost_estimate = self._estimate_cost(model_id, input_tokens, output_tokens)
            
            return {
                "text": generated_text,
                "model": model_id,
                "usage": response_body.get("usage", {}),
                "cost_estimate_usd": cost_estimate,
                "response_metadata": response.get("ResponseMetadata", {})
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message")
            logger.error(f"Bedrock API error [{error_code}]: {error_message}")
            raise RuntimeError(f"Bedrock request failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Unexpected error during model invocation: {e}")
            raise RuntimeError(f"Model invocation failed: {str(e)}")
    
    def _estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate the cost of a model invocation.
        Note: These are approximate rates and should be updated based on current AWS pricing.
        """
        # Approximate pricing per 1K tokens (as of 2024)
        pricing = {
            "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
            "claude-3-5-haiku-20241022": {"input": 0.00025, "output": 0.00125}
        }
        
        rates = pricing.get(model_id, {"input": 0.003, "output": 0.015})
        
        input_cost = (input_tokens / 1000) * rates["input"]
        output_cost = (output_tokens / 1000) * rates["output"]
        
        return input_cost + output_cost
    
    def list_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Return the configured models and their metadata."""
        return self.models
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model."""
        return self.models.get(model_id)


def create_bedrock_client(config_path: str = ".system2/config.yml") -> Optional[BedrockClient]:
    """
    Factory function to create a Bedrock client.
    Returns None if Bedrock is not available or not configured.
    """
    try:
        client = BedrockClient(config_path)
        if client.is_available():
            return client
        else:
            logger.warning("Bedrock client created but not available")
            return None
    except Exception as e:
        logger.error(f"Failed to create Bedrock client: {e}")
        return None


# Example usage
if __name__ == "__main__":
    # Test the client
    client = create_bedrock_client()
    if client:
        print("Available models:", client.list_available_models())
        
        try:
            response = client.invoke_model(
                "Hello, please respond with a brief greeting.",
                max_tokens=50
            )
            print(f"Response: {response['text']}")
            print(f"Cost estimate: ${response['cost_estimate_usd']:.4f}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Bedrock client not available")