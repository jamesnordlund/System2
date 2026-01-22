# AWS Bedrock Integration for System2

Add **enterprise-grade AI** to System2 with AWS Bedrock and Claude Sonnet 4.

## When to Use Bedrock

Choose Bedrock over native Claude when you need:
- **Enterprise compliance** (VPC, logging, governance)
- **Cost tracking** and usage controls
- **AWS integration** (IAM, CloudTrail, etc.)
- **Performance** optimized for your AWS region

## Quick Start

1. **Set AWS credentials**:
   ```bash
   export AWS_ACCESS_KEY_ID="your-key"
   export AWS_SECRET_ACCESS_KEY="your-secret"
   export AWS_DEFAULT_REGION="us-west-2"
   ```

2. **Enable Bedrock**: Set `default_provider: bedrock` in `.system2/config.yml`

3. **Test**: `python3 lib/bedrock_client.py`

## Configuration

System2 uses `.system2/config.yml` for provider configuration:

```yaml
providers:
  bedrock:
    enabled: true
    default_model: us.anthropic.claude-sonnet-4-20250514-v1:0
    region: us-west-2
    defaults:
      temperature: 0.7
      max_tokens: 4096

global:
  default_provider: native   # Native is default (change to 'bedrock' to enable)
```

## Available Models

| Model ID | Name | Description | Use Case |
|----------|------|-------------|----------|
| `us.anthropic.claude-sonnet-4-20250514-v1:0` | Claude Sonnet 4 | Most capable, advanced reasoning | Default for all agents |
| `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Claude Haiku 4.5 | Fastest, most economical | Quick tasks, coordination |

## Agent Configuration

### Claude Code Agents (.claude/agents/*.md)

```markdown
---
name: design-architect
model: claude-3-5-sonnet      # Native model name
provider: bedrock             # NEW: Use Bedrock
bedrockModel: us.anthropic.claude-sonnet-4-20250514-v1:0  # NEW: Bedrock inference profile ID
temperature: 0.3              # NEW: Override default
---
```

### Roo Code Modes (roo/*.yml)

```yaml
customModes:
  - slug: g-design-architect
    provider: bedrock           # NEW: Use Bedrock
    modelConfig:               # NEW: Bedrock configuration
      model: us.anthropic.claude-sonnet-4-20250514-v1:0
      temperature: 0.3
      max_tokens: 4096
```

## Authentication Options

| Method | Use Case | Configuration |
|--------|----------|---------------|
| **Environment vars** | Development | `export AWS_ACCESS_KEY_ID=...` |
| **AWS Profile** | Multi-account | `auth: { profile: my-profile }` |
| **IAM Role** | Production | `auth: { role_arn: arn:aws:... }` |

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
- **Claude Sonnet 4**: $0.003 input / $0.015 output
- **Claude Haiku 4.5**: $0.00025 input / $0.00125 output

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

| Issue | Solution |
|-------|----------|
| **Auth failed** | `aws sts get-caller-identity` |
| **Model access denied** | Add `bedrock:InvokeModel` permission |
| **Region error** | Use `us-west-2`, `us-east-1`, or `eu-west-1` |

**Required IAM permission**: `bedrock:InvokeModel` on Claude model resources.

## Migration Strategy

| Step | Action | Impact |
|------|--------|--------|
| **Phase 1** | Keep existing setup | Zero disruption |
| **Phase 2** | Add `provider: bedrock` to select agents | Gradual testing |
| **Phase 3** | Set `default_provider: bedrock` | Full migration |

**No code changes required** - existing workflows continue unchanged.