# PRIMEngine — AWS Deployment Guide

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  AWS Cloud                          │
│                                                     │
│  ┌─────────┐    ┌──────────────┐    ┌───────────┐  │
│  │   ALB   │───▶│  ECS Fargate │───▶│    RDS    │  │
│  │ (HTTPS) │    │  PRIMEngine  │    │PostgreSQL │  │
│  └─────────┘    │    API       │    └───────────┘  │
│       │         └──────┬───────┘                    │
│       │                │                            │
│       │         ┌──────▼───────┐    ┌───────────┐  │
│       │         │ ElastiCache  │    │CloudWatch │  │
│       │         │   (Redis)    │    │  Logs     │  │
│       │         └──────────────┘    └───────────┘  │
│       │                                             │
│  ┌────▼─────┐                                      │
│  │  Route53 │  api.primenergeia.com                │
│  └──────────┘                                      │
└─────────────────────────────────────────────────────┘
```

## Quick Start (Local)

```bash
# Run with Docker Compose
docker-compose up --build

# API available at http://localhost:8081
# Docs at http://localhost:8081/docs

# Test
curl http://localhost:8081/v1/health
curl -X POST http://localhost:8081/v1/dispatch/optimize \
  -H "X-API-Key: prime_dashboard_key" \
  -H "Content-Type: application/json" \
  -d '{"market":"ercot","fleet_mw":100,"duration_hours":24,"engine_type":"AICE","mission_profile":"Grid Peaking"}'
```

## AWS Deployment Steps

### 1. ECR — Push Docker Image

```bash
aws ecr create-repository --repository-name primengine
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker build -f Dockerfile.aws -t primengine:latest .
docker tag primengine:latest <account>.dkr.ecr.<region>.amazonaws.com/primengine:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/primengine:latest
```

### 2. ECS Fargate — Task Definition

- **CPU**: 1 vCPU (scale to 4 for enterprise)
- **Memory**: 2 GB (scale to 8 for enterprise)
- **Port**: 8081
- **Health check**: `GET /v1/health`
- **Environment variables**: Set API keys via AWS Secrets Manager

### 3. RDS PostgreSQL (Production)

Replace SQLite with PostgreSQL for production:
- **Instance**: db.t3.medium
- **Storage**: 20 GB gp3
- **Set** `PRIMENGINE_DB` env var to PostgreSQL connection string

### 4. ElastiCache Redis (Optional)

For session caching and rate limiting:
- **Instance**: cache.t3.micro
- **Use**: Rate limiting, dispatch result caching

### 5. ALB + Route53

- **ALB**: HTTPS termination with ACM certificate
- **Route53**: `api.primenergeia.com` → ALB
- **Health check**: `/v1/health`

### 6. CloudWatch

- **Logs**: Auto-captured from ECS tasks
- **Metrics**: Request count, latency, error rate
- **Alarms**: 5xx rate > 1%, latency > 5s

## AWS Marketplace Roadmap

1. **SaaS listing** with contract-based pricing
2. **Metering API** integration for usage-based billing
3. **Partner badge** via AWS ISV Accelerate program

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PRIME_API_KEY_PILOT` | Pilot tier API key | `prime_pilot_key` |
| `PRIME_API_KEY_DASHBOARD` | Dashboard tier API key | `prime_dashboard_key` |
| `PRIME_API_KEY_API` | API tier API key | `prime_api_key` |
| `PRIME_API_KEY_ENTERPRISE` | Enterprise tier API key | `prime_enterprise_key` |
| `PRIMENGINE_DATA_DIR` | Data directory path | `~/.prime_api` |
| `PRIMENGINE_DB` | Database path/URL | `~/.prime_api/primengine.db` |
| `PRIME_TELEGRAM_BOT_TOKEN` | Telegram bot token | (disabled) |
| `PRIME_TELEGRAM_CHAT_ID` | Telegram chat ID | (disabled) |

## Cost Estimate (Monthly)

| Service | Config | Cost |
|---------|--------|------|
| ECS Fargate | 1 vCPU, 2GB, always-on | ~$30 |
| RDS PostgreSQL | db.t3.micro | ~$15 |
| ALB | Standard | ~$20 |
| Route53 | 1 hosted zone | ~$1 |
| **Total** | | **~$66/mo** |

Scale to enterprise (4 vCPU, 8GB, multi-AZ RDS): ~$300/mo
