# AWS Bedrock Integration for System2

System2 now defaults to AWS Bedrock with Claude 3.5 Sonnet for enterprise-grade AI model serving.

## Quick Start

1. **Configure AWS credentials** (choose one):
   ```bash
   # Option 1: Environment variables
   export AWS_ACCESS_KEY_ID="your-key"
   export AWS_SECRET_ACCESS_KEY="your-secret"
   export AWS_DEFAULT_REGION="us-west-2"
   
   # Option 2: AWS CLI profile
   aws configure --profile default
   
   # Option 3: IAM role (for EC2/ECS environments)
   # Automatically detected
   ```

2. **Verify Bedrock access**:
   ```bash
   python3 lib/bedrock_client.py
   ```

3. **Start using System2** - Bedrock is now the default provider!

## Configuration

System2 uses `.system2/config.yml` for provider configuration:

```yaml
providers:
  bedrock:
    enabled: true
    default_model: claude-3-5-sonnet-20241022
    region: us-west-2
    defaults:
      temperature: 0.7
      max_tokens: 4096

global:
  default_provider: bedrock  # Default to Bedrock
```

## Available Models

| Model ID | Name | Description | Use Case |
|----------|------|-------------|----------|
| `claude-3-5-sonnet-20241022` | Claude 3.5 Sonnet | Most capable, balanced | Default for all agents |
| `claude-3-5-haiku-20241022` | Claude 3.5 Haiku | Fastest, most economical | Quick tasks, coordination |

## Agent Configuration

### Claude Code Agents (.claude/agents/*.md)

```markdown
---
name: design-architect
model: claude-3-5-sonnet      # Native model name
provider: bedrock             # NEW: Use Bedrock
bedrockModel: claude-3-5-sonnet-20241022  # NEW: Bedrock model ID
temperature: 0.3              # NEW: Override default
---
```

### Roo Code Modes (roo/*.yml)

```yaml
customModes:
  - slug: g-design-architect
    provider: bedrock           # NEW: Use Bedrock
    modelConfig:               # NEW: Bedrock configuration
      model: claude-3-5-sonnet-20241022
      temperature: 0.3
      max_tokens: 4096
```

## Authentication Methods

### 1. Environment Variables (Recommended for Development)
```bash
export AWS_ACCESS_KEY_ID="AKIAEXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export AWS_DEFAULT_REGION="us-west-2"
```

### 2. AWS Profile
```yaml
# .system2/config.yml
providers:
  bedrock:
    auth:
      profile: my-profile
```

### 3. IAM Role Assumption
```yaml
# .system2/config.yml
providers:
  bedrock:
    auth:
      role_arn: arn:aws:iam::123456789012:role/System2BedrockRole
```

## Cost Management

Bedrock usage is tracked with cost estimates:

```yaml
# .system2/config.yml
global:
  cost_controls:
    session_cost_warning_usd: 5.0
    max_tokens_per_request: 8192
```

Approximate costs (per 1K tokens):
- **Claude 3.5 Sonnet**: $0.003 input / $0.015 output
- **Claude 3.5 Haiku**: $0.00025 input / $0.00125 output

## Fallback Behavior

If Bedrock is unavailable, System2 automatically falls back to native providers:

```yaml
# .system2/config.yml
providers:
  native:
    fallback: true
    fallback_timeout: 10
```

## Troubleshooting

### Authentication Issues
```bash
# Check AWS credentials
aws sts get-caller-identity

# Test Bedrock access
aws bedrock list-foundation-models --region us-west-2
```

### Permission Requirements
Your AWS credentials need:
- `bedrock:InvokeModel`
- `bedrock:ListFoundationModels`

Example IAM policy:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20241022-v1:0",
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"
            ]
        }
    ]
}
```

### Model Availability
Claude 3.5 models are available in these regions:
- `us-west-2` (Oregon) - Recommended
- `us-east-1` (N. Virginia)
- `eu-west-1` (Ireland)

## Migration from Native

System2 maintains full backward compatibility. To migrate:

1. **Keep existing agents/modes unchanged** - they continue working with native providers
2. **Gradually opt-in to Bedrock** by adding `provider: bedrock` to specific agents
3. **Update global default** when ready: `default_provider: bedrock`

No code changes required for existing System2 workflows!