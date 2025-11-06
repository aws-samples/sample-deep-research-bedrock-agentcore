# Testing Guide - Lambda + Gateway 독립 테스트

이 모듈은 **AgentCore Runtime 없이** Lambda + Gateway만 독립적으로 배포하고 테스트합니다.

## 🎯 목적

- ✅ **빠른 테스트**: 컨테이너 이미지 빌드 없이 Lambda + Gateway만 배포 (1-2분)
- ✅ **독립 검증**: 각 Lambda 함수가 올바르게 동작하는지 확인
- ✅ **Gateway 연결 확인**: MCP 프로토콜 통신 테스트
- ✅ **유닛 테스트 후 통합**: 검증된 후 메인 IaC에 통합

---

## 📋 테스트 레벨

### **Level 1: Lambda 함수 테스트** (가장 빠름)

Lambda 함수만 직접 호출합니다.

```bash
# 1. 배포
export TAVILY_API_KEY="your-key"
cd scripts
./deploy.sh

# 2. Lambda 함수명 확인
LAMBDA_NAME=$(cd ../terraform && terraform output -raw tavily_lambda_name)

# 3. Lambda 직접 호출 (Gateway 우회)
aws lambda invoke \
  --function-name $LAMBDA_NAME \
  --payload '{"query":"Claude AI","search_depth":"basic"}' \
  --cli-binary-format raw-in-base64-out \
  response.json

# 4. 결과 확인
cat response.json | jq '.'
```

**테스트 내용**:
- Lambda 함수 실행 성공 여부
- Tavily API 호출 정상 작동
- 응답 형식 확인

**장점**: Gateway 없이도 테스트 가능, 가장 빠름

---

### **Level 2: Gateway 연결 테스트**

Gateway를 통해 Lambda 호출 (MCP 프로토콜 사용)

```bash
# 1. 테스트 의존성 설치
pip install -r scripts/test-requirements.txt

# 2. Gateway 테스트 실행
python3 scripts/test-gateway.py
```

**테스트 내용**:
- Gateway IAM 인증 (SigV4)
- MCP 세션 초기화
- Tools 목록 조회
- Tool 호출 (tavily_search)

**장점**: 실제 Agent Runtime과 동일한 방식으로 테스트

---

### **Level 3: Agent Runtime 통합 테스트** (다음 단계)

실제 Agent Runtime 컨테이너에서 Gateway 사용

```python
# Agent Runtime에서
async with streamablehttp_client_with_sigv4(
    url=gateway_url,
    credentials=credentials,
    service='bedrock-agentcore',
    region='us-west-2'
) as (read, write, _):
    async with ClientSession(read, write) as session:
        tools = await load_mcp_tools(session)
        # ... use tools in agent
```

---

## 🔍 로그 확인

### Lambda 로그
```bash
# 실시간 로그 스트림
aws logs tail /aws/lambda/$LAMBDA_NAME --follow

# 최근 1시간 로그
aws logs tail /aws/lambda/$LAMBDA_NAME --since 1h
```

### Gateway 로그
Gateway 자체는 CloudWatch에 로그를 남기지 않지만, Lambda 호출 로그를 확인할 수 있습니다.

---

## ⚡ 배포 시간 비교

| 구성 | 시간 | 포함 사항 |
|------|------|-----------|
| **이 모듈** (Lambda + Gateway만) | 1-2분 | Lambda, Gateway, IAM |
| **전체 스택** (Runtime 포함) | 10-15분 | + ECR, Docker 빌드, Runtime |

**결론**: 이 모듈은 전체 배포 대비 **5-10배 빠름** ⚡

---

## 🧪 테스트 체크리스트

### ✅ Lambda 함수 테스트
- [ ] Lambda 배포 성공
- [ ] 직접 호출 성공 (aws lambda invoke)
- [ ] Tavily API 응답 정상
- [ ] 에러 핸들링 확인

### ✅ Gateway 연결 테스트
- [ ] Gateway 생성 성공
- [ ] SigV4 인증 성공
- [ ] MCP 세션 초기화
- [ ] Tools 목록 조회
- [ ] Tool 호출 성공

### ✅ 통합 준비
- [ ] gateway_config.json 생성 확인
- [ ] IAM 권한 검증
- [ ] 메인 IaC 통합 가능

---

## 🐛 트러블슈팅

### Lambda 호출 실패
```bash
# CloudWatch 로그 확인
aws logs tail /aws/lambda/$LAMBDA_NAME --since 5m

# 일반적인 원인:
# 1. Tavily API Key 없음 → Secrets Manager 확인
# 2. 타임아웃 → Lambda timeout 증가
# 3. 권한 부족 → IAM 역할 확인
```

### Gateway 연결 실패
```bash
# Gateway 상태 확인
GATEWAY_ID=$(cd terraform && terraform output -raw gateway_id)
aws bedrock-agentcore-control get-gateway \
  --gateway-identifier $GATEWAY_ID \
  --region us-west-2

# IAM 권한 확인
aws sts get-caller-identity
# → 현재 사용자에게 bedrock-agentcore:InvokeGateway 권한 필요
```

### Tavily API 에러
```bash
# API Key 확인
SECRET_ARN=$(cd terraform && terraform output -raw tavily_api_key_secret_arn)
aws secretsmanager get-secret-value \
  --secret-id $SECRET_ARN \
  --query SecretString \
  --output text

# API 직접 테스트
curl -X POST https://api.tavily.com/search \
  -H "Content-Type: application/json" \
  -d '{"api_key":"your-key","query":"test","max_results":1}'
```

---

## 📦 메인 IaC 통합

테스트 성공 후 메인 Terraform에 통합:

### **Option 1: Module로 통합**

```hcl
# main.tf
module "research_gateways" {
  source = "./research-gateway-lambdas/terraform"

  tavily_api_key = var.tavily_api_key
  environment    = var.environment
  project_name   = "research-gateway"
}

# gateway_config.json 자동 생성
resource "local_file" "gateway_config" {
  content  = jsonencode(module.research_gateways.gateway_config)
  filename = "${path.module}/agent-runtime/gateway_config.json"
}
```

### **Option 2: Remote State 사용**

```hcl
# Gateway는 별도 배포 유지
# main.tf에서 outputs 참조
data "terraform_remote_state" "gateways" {
  backend = "s3"
  config = {
    bucket = "terraform-state"
    key    = "research-gateways/terraform.tfstate"
    region = "us-west-2"
  }
}

# Agent Runtime에서 Gateway URL 사용
resource "aws_bedrockagentcore_runtime" "agent" {
  environment_variables = {
    GATEWAY_URL = data.terraform_remote_state.gateways.outputs.gateway_url
  }
}
```

---

## 🚀 권장 워크플로우

```
1. Lambda + Gateway 개발
   ├─ 로컬 테스트 (test-lambda-local.py)
   └─ 코드 수정

2. 독립 배포 (이 모듈)
   ├─ ./scripts/deploy.sh
   └─ Lambda 직접 테스트

3. Gateway 연결 테스트
   ├─ test-gateway.py
   └─ MCP 통신 확인

4. 메인 IaC 통합
   ├─ Module로 추가
   └─ Agent Runtime 배포

5. End-to-End 테스트
   └─ 전체 workflow 실행
```

---

## 📊 성능 메트릭

### Lambda Cold Start
- **requests만**: ~500ms
- **yfinance (Layer)**: ~2-3초

### Gateway Overhead
- MCP 프로토콜: ~50-100ms
- SigV4 서명: ~10-20ms

### 전체 레이턴시
```
Client → Gateway → Lambda → Tavily API
  10ms     50ms      500ms      1-2s
= Total: ~2.5-3초 (첫 호출)
= Warm: ~1.5-2초 (이후 호출)
```

---

## ✅ 다음 단계

1. [ ] Tavily Lambda 테스트 완료
2. [ ] Google Search Lambda 추가
3. [ ] ArXiv Lambda 추가
4. [ ] Finance Lambda + Layer 추가
5. [ ] Multi-Gateway 설정
6. [ ] Agent Runtime 통합
