# Dependencies Version Guide

Updated: 2024-10-29

## 📦 Lambda Dependencies

**File**: `lambdas/tavily/requirements.txt`

```
requests==2.32.5
```

### Why so minimal?

1. ✅ **boto3/botocore** - Already included in Lambda runtime (no need to package)
2. ✅ **requests** - Small library (~500KB), safe to include
3. ✅ **certifi, urllib3, etc.** - Auto-installed as requests dependencies

### Package Size
- requests + dependencies: **~2-3 MB**
- Well under Lambda 50MB limit ✅

---

## 🧪 Test Dependencies

**File**: `scripts/test-requirements.txt`

```
boto3==1.40.62
```

### Why boto3 only?

Most testing needs just AWS CLI commands:
```bash
aws lambda invoke --function-name ...
aws logs tail /aws/lambda/...
aws secretsmanager get-secret-value ...
```

### Optional Advanced Testing

For Gateway MCP protocol testing (`test-gateway.py`), uncomment:
```
# mcp==1.19.0
# httpx==0.28.1
# botocore==1.40.62
```

**When you need this**:
- Debugging Gateway MCP communication
- Testing SigV4 authentication flows
- Developing new Gateway features

**When you DON'T need this**:
- Basic Lambda testing ✅
- CloudWatch log review ✅
- Integration testing ✅

---

## 🔍 Version Selection Rationale

### requests==2.32.5
- **Latest stable** (Oct 2024)
- Python 3.13 compatible ✅
- Security patches included
- No breaking changes from 2.31.x

### boto3==1.40.62
- **Latest stable** (Oct 2024)
- AWS service updates included
- Compatible with Lambda runtime ✅
- Note: boto3 updates frequently (daily/weekly)

### mcp==1.19.0 (optional)
- **Latest stable** (Oct 2024)
- MCP protocol version: 2024-11-05
- Async/await support
- httpx client integration

### httpx==0.28.1 (optional)
- **Latest stable** (Oct 2024)
- HTTP/2 support
- Async client
- Auth extension (for SigV4)

---

## 🚀 Updating Dependencies

### For Lambda (requests)

```bash
# Check latest version
pip index versions requests

# Update requirements.txt
echo "requests==NEW_VERSION" > lambdas/tavily/requirements.txt

# Test locally
cd lambdas/tavily
pip install -r requirements.txt
python3 test_imports.py

# Rebuild and redeploy
cd ../../scripts
./deploy.sh
```

### For Testing (boto3)

```bash
# Check latest
pip index versions boto3

# Update
echo "boto3==NEW_VERSION" > scripts/test-requirements.txt

# Test
pip install -r scripts/test-requirements.txt
python3 scripts/test-lambda-local.py
```

---

## ⚠️ Version Pinning Strategy

### Why Pin Exact Versions?

```
❌ requests>=2.31.0    # BAD: Unpredictable
✅ requests==2.32.5    # GOOD: Reproducible
```

**Benefits**:
1. Reproducible builds
2. No surprise breaking changes
3. Easier debugging
4. Faster CI/CD (dependency cache)

### When to Update

✅ **Update regularly**:
- Security patches
- Python version compatibility
- AWS service updates (boto3)

❌ **Don't update blindly**:
- Test after each update
- Check release notes
- Monitor for breaking changes

---

## 📊 Package Sizes

| Package | Size | Lambda Impact |
|---------|------|---------------|
| requests | ~600 KB | Included ✅ |
| boto3 | ~10 MB | Runtime ❌ |
| botocore | ~12 MB | Runtime ❌ |
| mcp | ~2 MB | Not needed ❌ |
| httpx | ~1.5 MB | Not needed ❌ |

**Current Lambda package**: ~3 MB (requests + code)

---

## 🔐 Security Considerations

### Dependency Scanning

```bash
# Check for vulnerabilities
pip install safety
safety check -r lambdas/tavily/requirements.txt
```

### Update Frequency

- **requests**: Every 2-3 months (security focus)
- **boto3**: Monthly (AWS features)
- **mcp**: As needed (protocol updates)

### Audit Trail

This file serves as audit trail for dependency updates:
- Date of update: 2024-10-29
- Previous versions: See git history
- Reason: Modernize to latest stable versions

---

## 🛠️ Troubleshooting

### Lambda ImportError

```
ERROR: Unable to import module 'lambda_function': No module named 'requests'
```

**Fix**: Rebuild deployment package
```bash
cd scripts
./build-tavily-lambda.sh
./deploy.sh
```

### Version Conflicts

```
ERROR: Package 'requests' requires different version
```

**Fix**: Use exact versions (==) not ranges (>=)

### Large Package Size

```
ERROR: Deployment package size exceeds 50MB
```

**Fix**:
1. Remove boto3 from requirements (use Lambda runtime)
2. Use Lambda Layers for heavy packages (pandas, numpy)
3. Optimize with `find . -name "*.pyc" -delete`

---

## 📚 References

- [AWS Lambda Runtimes](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html)
- [Python Package Index](https://pypi.org/)
- [requests Documentation](https://requests.readthedocs.io/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [MCP Protocol](https://github.com/modelcontextprotocol/specification)
