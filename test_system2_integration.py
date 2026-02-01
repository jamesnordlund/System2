#!/usr/bin/env python3
"""
System2 Bedrock Integration Test Suite

Tests the full System2 configuration and provider selection workflow,
simulating how agents and modes would use the Bedrock integration.
"""

import os
import sys
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from bedrock_client import create_bedrock_client, BedrockClient

class System2ConfigManager:
    """Simulates System2's configuration management"""
    
    def __init__(self, config_path: str = '.system2/config.yml'):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load System2 configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"❌ Config file not found: {self.config_path}")
            return {}
        except yaml.YAMLError as e:
            print(f"❌ Invalid YAML in config: {e}")
            return {}
    
    def get_default_provider(self) -> str:
        """Get the default provider from global config"""
        return self.config.get('global', {}).get('default_provider', 'native')
    
    def get_bedrock_config(self) -> Dict[str, Any]:
        """Get Bedrock-specific configuration"""
        return self.config.get('providers', {}).get('bedrock', {})

class System2Agent:
    """Simulates a System2 Claude Code agent"""
    
    def __init__(self, name: str, frontmatter: Dict[str, Any], config_manager: System2ConfigManager):
        self.name = name
        self.frontmatter = frontmatter
        self.config_manager = config_manager
        self.bedrock_client: Optional[BedrockClient] = None
    
    def get_effective_provider(self) -> str:
        """Determine which provider this agent should use"""
        # Agent-level override takes precedence
        if 'provider' in self.frontmatter:
            return self.frontmatter['provider']
        
        # Fall back to global default
        return self.config_manager.get_default_provider()
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration for this agent"""
        provider = self.get_effective_provider()
        
        if provider == 'bedrock':
            bedrock_config = self.config_manager.get_bedrock_config()
            return {
                'model': self.frontmatter.get('bedrockModel') or bedrock_config.get('default_model'),
                'temperature': self.frontmatter.get('temperature') or bedrock_config.get('temperature', 0.7),
                'max_tokens': self.frontmatter.get('max_tokens') or bedrock_config.get('max_tokens', 4096),
                'region': bedrock_config.get('region', 'us-west-2')
            }
        else:
            # Native provider config
            return {
                'model': self.frontmatter.get('model', 'claude-3-5-sonnet'),
                'temperature': self.frontmatter.get('temperature', 0.7),
                'max_tokens': self.frontmatter.get('max_tokens', 4096)
            }
    
    def initialize_bedrock(self) -> bool:
        """Initialize Bedrock client if needed"""
        if self.get_effective_provider() == 'bedrock':
            self.bedrock_client = create_bedrock_client()
            return self.bedrock_client is not None
        return True
    
    def invoke(self, prompt: str) -> Dict[str, Any]:
        """Invoke the agent with a prompt"""
        provider = self.get_effective_provider()
        model_config = self.get_model_config()
        
        if provider == 'bedrock':
            if not self.bedrock_client:
                raise RuntimeError("Bedrock client not initialized")
            
            return self.bedrock_client.invoke_model(
                prompt,
                model_id=model_config['model'],
                temperature=model_config['temperature'],
                max_tokens=model_config['max_tokens']
            )
        else:
            # Simulate native provider response
            return {
                'text': f"[SIMULATED NATIVE] Response from {model_config['model']} for agent {self.name}",
                'model': model_config['model'],
                'usage': {'input_tokens': 10, 'output_tokens': 15},
                'cost_estimate_usd': 0.0001,
                'provider': 'native'
            }

def test_configuration_loading():
    """Test 1: Configuration Loading"""
    print("\n🧪 Test 1: Configuration Loading")
    
    config_manager = System2ConfigManager()
    
    if not config_manager.config:
        print("❌ Failed to load configuration")
        return False
    
    print("✅ Configuration loaded successfully")
    print(f"   Default provider: {config_manager.get_default_provider()}")
    
    bedrock_config = config_manager.get_bedrock_config()
    if bedrock_config:
        print(f"   Bedrock enabled: {bedrock_config.get('enabled', False)}")
        print(f"   Default model: {bedrock_config.get('default_model', 'not set')}")
        print(f"   Region: {bedrock_config.get('region', 'not set')}")
    
    return True

def test_agent_provider_selection():
    """Test 2: Agent Provider Selection Logic"""
    print("\n🧪 Test 2: Agent Provider Selection Logic")
    
    config_manager = System2ConfigManager()
    
    # Test agent with native provider (default)
    native_agent = System2Agent(
        "test-native",
        {'name': 'test-native', 'model': 'claude-3-5-sonnet'},
        config_manager
    )
    
    # Test agent with bedrock override
    bedrock_agent = System2Agent(
        "test-bedrock",
        {
            'name': 'test-bedrock',
            'provider': 'bedrock',
            'bedrockModel': 'us.anthropic.claude-sonnet-4-20250514-v1:0',
            'temperature': 0.3
        },
        config_manager
    )
    
    print(f"✅ Native agent provider: {native_agent.get_effective_provider()}")
    print(f"✅ Bedrock agent provider: {bedrock_agent.get_effective_provider()}")
    
    # Test model configurations
    native_config = native_agent.get_model_config()
    bedrock_config = bedrock_agent.get_model_config()
    
    print(f"   Native config: {json.dumps(native_config, indent=2)}")
    print(f"   Bedrock config: {json.dumps(bedrock_config, indent=2)}")
    
    return True

def test_bedrock_initialization():
    """Test 3: Bedrock Client Initialization"""
    print("\n🧪 Test 3: Bedrock Client Initialization")
    
    config_manager = System2ConfigManager()
    
    bedrock_agent = System2Agent(
        "bedrock-test",
        {'name': 'bedrock-test', 'provider': 'bedrock'},
        config_manager
    )
    
    if bedrock_agent.initialize_bedrock():
        print("✅ Bedrock client initialized successfully")
        if bedrock_agent.bedrock_client:
            models = bedrock_agent.bedrock_client.list_available_models()
            print(f"   Available models: {list(models.keys())}")
        return True
    else:
        print("❌ Bedrock client initialization failed")
        return False

def test_agent_invocation():
    """Test 4: Agent Invocation"""
    print("\n🧪 Test 4: Agent Invocation")
    
    config_manager = System2ConfigManager()
    
    # Test native agent invocation
    print("   Testing native agent...")
    native_agent = System2Agent(
        "native-test",
        {'name': 'native-test', 'model': 'claude-3-5-sonnet'},
        config_manager
    )
    
    try:
        native_response = native_agent.invoke("Test prompt for native agent")
        print(f"✅ Native agent response: {native_response['text'][:50]}...")
    except Exception as e:
        print(f"❌ Native agent failed: {e}")
        return False
    
    # Test Bedrock agent invocation
    print("   Testing Bedrock agent...")
    bedrock_agent = System2Agent(
        "bedrock-test", 
        {
            'name': 'bedrock-test',
            'provider': 'bedrock',
            'bedrockModel': 'us.anthropic.claude-sonnet-4-20250514-v1:0'
        },
        config_manager
    )
    
    if not bedrock_agent.initialize_bedrock():
        print("❌ Bedrock agent initialization failed - skipping invocation test")
        return False
    
    try:
        bedrock_response = bedrock_agent.invoke("Test prompt for Bedrock agent")
        print(f"✅ Bedrock agent response: {bedrock_response['text'][:50]}...")
        print(f"   Cost: ${bedrock_response['cost_estimate_usd']:.4f}")
        print(f"   Model: {bedrock_response['model']}")
    except Exception as e:
        print(f"❌ Bedrock agent failed: {e}")
        return False
    
    return True

def test_fallback_behavior():
    """Test 5: Fallback Behavior"""
    print("\n🧪 Test 5: Fallback Behavior")
    
    # Simulate a scenario where Bedrock is configured but fails
    config_manager = System2ConfigManager()
    
    bedrock_agent = System2Agent(
        "fallback-test",
        {'name': 'fallback-test', 'provider': 'bedrock'},
        config_manager
    )
    
    # Test what happens when Bedrock initialization fails
    original_bedrock_client = bedrock_agent.bedrock_client
    bedrock_agent.bedrock_client = None  # Simulate failure
    
    try:
        # This should fail gracefully
        bedrock_agent.invoke("Test fallback")
        print("❌ Expected fallback failure didn't occur")
        return False
    except RuntimeError:
        print("✅ Proper error handling when Bedrock unavailable")
    
    # Test fallback to native
    print("   Testing manual fallback to native...")
    bedrock_agent.frontmatter['provider'] = 'native'
    fallback_response = bedrock_agent.invoke("Test native fallback")
    print(f"✅ Fallback response: {fallback_response['text'][:50]}...")
    
    return True

def run_integration_tests():
    """Run all System2 integration tests"""
    print("🚀 System2 Bedrock Integration Test Suite")
    print("=" * 50)
    
    tests = [
        test_configuration_loading,
        test_agent_provider_selection,
        test_bedrock_initialization,
        test_agent_invocation,
        test_fallback_behavior
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All System2 integration tests passed!")
        return True
    else:
        print("⚠️  Some tests failed - check configuration and AWS access")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)