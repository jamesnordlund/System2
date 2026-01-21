# Pull Request Proposal: AWS Bedrock Claude 3.5 Sonnet Integration

## Summary

This PR adds **optional AWS Bedrock support** to System2, enabling enterprise-grade AI model serving with Claude 3.5 Sonnet while maintaining native Claude providers as the default.

## Key Features

### 🚀 **Optional Bedrock Provider**
- Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`) available via AWS Bedrock
- Native providers (Claude Code CLI/Roo Code) remain the default
- Easy opt-in configuration - set `default_provider: bedrock` when needed
- Zero breaking changes - existing workflows continue working

### 🔐 **Enterprise Authentication**
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- AWS profiles (`~/.aws/credentials`) 
- IAM role assumption for production environments
- Secure credential handling (no secrets in config files)

### 💰 **Cost Management & Monitoring**
- Real-time cost estimation for all requests
- Configurable cost warnings and limits
- Model-specific pricing awareness
- Request logging (no sensitive data exposed)

### ⚙️ **Flexible Configuration**
- Global configuration via `.system2/config.yml`
- Per-agent overrides in Claude Code agents
- Per-mode overrides in Roo Code modes
- Temperature, max_tokens, and other parameter tuning

## Files Changed

```
.system2/config.yml     (NEW) - Global configuration
lib/bedrock_client.py   (NEW) - Bedrock integration client  
BEDROCK.md             (NEW) - Comprehensive setup guide
README.md              (MODIFIED) - Added model provider info
```

## Configuration Example

### Global Settings (`.system2/config.yml`)
```yaml
providers:
  bedrock:
    enabled: true
    default_model: claude-3-5-sonnet-20241022
    region: us-west-2

global:
  default_provider: native   # 🎯 Native remains default (opt-in to bedrock)
```

### Agent Override (`.claude/agents/design-architect.md`)
```yaml
---
name: design-architect
provider: bedrock
bedrockModel: claude-3-5-sonnet-20241022
temperature: 0.3
---
```

## Benefits

1. **🏢 Enterprise Ready**: AWS Bedrock provides enterprise-grade security, compliance, and governance
2. **⚡ Performance**: Access to latest Claude 3.5 capabilities with optimized AWS infrastructure  
3. **💵 Cost Control**: Bedrock pricing model with built-in usage tracking
4. **🔄 Reliability**: Automatic fallback ensures uninterrupted workflows
5. **📈 Scalability**: Enterprise features like VPC endpoints, CloudTrail logging, etc.

## Quick Start

1. **Set AWS credentials**:
   ```bash
   export AWS_ACCESS_KEY_ID="your-key"
   export AWS_SECRET_ACCESS_KEY="your-secret"
   export AWS_DEFAULT_REGION="us-west-2"
   ```

2. **Test integration**:
   ```bash
   python3 lib/bedrock_client.py
   ```

3. **Enable Bedrock** - Set `default_provider: bedrock` in `.system2/config.yml`!

## Testing Guidance

The implementation includes:
- ✅ Authentication validation
- ✅ Model availability checks  
- ✅ Error handling and fallback
- ✅ Cost estimation
- ✅ Configuration validation

### Test Commands
```bash
# Test Bedrock client
python3 lib/bedrock_client.py

# Verify AWS access
aws bedrock list-foundation-models --region us-west-2

# Check configuration
cat .system2/config.yml
```

## Migration Path

**Zero-disruption migration**:

1. **Phase 1**: Existing users continue with native providers automatically
2. **Phase 2**: Users can opt-in by configuring AWS credentials  
3. **Phase 3**: Bedrock becomes default for new setups (this PR)
4. **Phase 4**: Users migrate individual agents/modes as needed

## Backward Compatibility

- ✅ All existing `.claude/agents/*.md` files work unchanged
- ✅ All existing `roo/*.yml` modes work unchanged  
- ✅ Native providers remain available as fallback
- ✅ No CLI changes required
- ✅ No workflow modifications needed

## Required AWS Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20241022-v1:0",
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"
            ]
        }
    ]
}
```

## Documentation

- 📖 **BEDROCK.md**: Complete setup and configuration guide
- 📖 **README.md**: Updated with model provider information  
- 📖 **Inline code docs**: Comprehensive docstrings and comments

## Impact Assessment

- **Breaking Changes**: None
- **Performance Impact**: Positive (faster model access via AWS)
- **Security Impact**: Enhanced (enterprise-grade AWS security)
- **Maintenance Burden**: Minimal (well-architected, documented code)

## Future Considerations

This implementation provides a foundation for:
- Additional Bedrock models (Claude Opus, other providers)
- Advanced Bedrock features (custom models, guardrails)
- Cost optimization and usage analytics
- Multi-region deployment strategies

## Review Focus Areas

1. **Security**: Credential handling and authentication flow
2. **Backward Compatibility**: Existing workflow preservation
3. **Error Handling**: Fallback mechanisms and user experience  
4. **Documentation**: Setup clarity and troubleshooting guidance
5. **Configuration**: Flexibility and sensible defaults

---

**Ready for review and merge!** 🚀

This PR enables System2 to leverage AWS Bedrock's enterprise capabilities while maintaining the framework's core principles of deliberate, spec-driven engineering workflows.