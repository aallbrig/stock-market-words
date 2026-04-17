# ADR: SQLite Database Backup to AWS S3

**Status:** Accepted
**Date:** 2026-04-17
**Deciders:** aallbright

## Context

The Stock Market Words data pipeline persists ~74 MB of market data in a
SQLite database (`data/market_data.db`). This database is the canonical
store of historical ticker data, daily metrics, and strategy scores. It
grows by ~1–2 MB per trading day.

The pipeline runs on an always-on ThinkPad via systemd timer. If the
database is lost (disk failure, accidental deletion), all historical data
is gone — re-fetching from Yahoo Finance would take days and some
historical data may be unavailable.

We need a cheap, automated, off-site backup with minimal AWS permissions.

## Decision

### Storage: S3 One Zone-IA with 30-day lifecycle expiration

- **Bucket:** `smw-database-backups` (us-east-1)
- **Key pattern:** `daily-backups/market_data_YYYY-MM-DD.db`
- **Storage class:** `ONEZONE_IA` ($0.01/GB/mo)
- **Encryption:** SSE-S3 (AES-256, free)
- **Retention:** 30-day expiration via lifecycle rule
- **Public access:** Blocked on all four dimensions

**Why One Zone-IA:** At ~3 GB/month stored, cost is ~$0.03/mo. Standard
S3 would be $0.07/mo — both trivial, but One Zone-IA is the cheapest
option with instant retrieval. Single-AZ is acceptable for a hobby
project with 30 days of rolling backups.

**Why not Glacier:** Instant retrieval matters when restoring from a
disaster. Glacier Instant Retrieval is slightly cheaper ($0.004/GB) but
has 90-day minimum billing — overkill for 30-day retention.

### Backup method: `sqlite3 .backup` → `aws s3 cp`

1. Use SQLite's `.backup` command to create a consistent point-in-time
   snapshot (safe even if the DB is in WAL mode).
2. Verify integrity with `PRAGMA integrity_check`.
3. Upload to S3 with SSE-S3 encryption, ONEZONE_IA storage class, and
   metadata tags.

This runs as an `ExecStartPost` in the systemd service, after the
pipeline completes and the git commit/push succeeds.

### IAM: Dedicated user with inline policy (least privilege)

A new IAM user `smw-backup-user` gets an inline policy scoped to:

- **s3:PutObject** — only to `arn:aws:s3:::smw-database-backups/daily-backups/*`
- **s3:PutObjectTagging** — same prefix
- **s3:ListBucket** — same prefix (for verification)
- **s3:GetObject** — same prefix (for restore)
- **Deny s3:PutObject without SSE** — enforced via condition key

The user has **no** permissions to:
- Delete objects (lifecycle rules handle cleanup)
- Access any other bucket
- Use any other AWS service
- Modify bucket configuration

**Why an IAM user (not a role):** IAM roles require an identity provider
(OIDC, STS federation) which adds significant complexity for an on-prem
machine. A dedicated IAM user with long-lived access keys stored in
1Password and deployed to the ThinkPad's `~smw/.aws/credentials` is the
simplest secure pattern for this use case.

**Key rotation:** Rotate access keys every 90 days. Document in the
`verify.sh` script as a manual check.

## IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowBackupUpload",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectTagging"
      ],
      "Resource": "arn:aws:s3:::smw-database-backups/daily-backups/*",
      "Condition": {
        "StringEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    },
    {
      "Sid": "AllowListForVerification",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::smw-database-backups",
      "Condition": {
        "StringLike": {
          "s3:prefix": "daily-backups/*"
        }
      }
    },
    {
      "Sid": "AllowGetForRestore",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::smw-database-backups/daily-backups/*"
    },
    {
      "Sid": "DenyUnencryptedUploads",
      "Effect": "Deny",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::smw-database-backups/daily-backups/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    }
  ]
}
```

## S3 Bucket Setup

```bash
# Create bucket
aws s3api create-bucket --bucket smw-database-backups --region us-east-1

# Block ALL public access
aws s3api put-public-access-block --bucket smw-database-backups \
  --public-access-block-configuration \
  'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true'

# Default encryption (SSE-S3)
aws s3api put-bucket-encryption --bucket smw-database-backups \
  --server-side-encryption-configuration '{
    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
  }'

# 30-day lifecycle expiration
aws s3api put-bucket-lifecycle-configuration --bucket smw-database-backups \
  --lifecycle-configuration '{
    "Rules": [{
      "Id": "DeleteOldBackups",
      "Status": "Enabled",
      "Filter": {"Prefix": "daily-backups/"},
      "Expiration": {"Days": 30}
    }]
  }'
```

## Cost Estimate

| Component | Quantity | Rate | Monthly Cost |
|-----------|----------|------|-------------|
| S3 One Zone-IA storage | ~2–3 GB avg | $0.01/GB | $0.02–0.03 |
| PUT requests | ~20/mo | $0.005/10k | ~$0.00 |
| LIST requests | ~20/mo | $0.004/10k | ~$0.00 |
| Encryption (SSE-S3) | — | free | $0.00 |
| **Total** | | | **~$0.03–0.05/mo** |

## Disaster Recovery

```bash
# List available backups
aws s3 ls s3://smw-database-backups/daily-backups/ --profile smw-backup

# Download a specific backup
aws s3 cp s3://smw-database-backups/daily-backups/market_data_2026-04-17.db \
  /tmp/restored.db --profile smw-backup

# Verify integrity
sqlite3 /tmp/restored.db "PRAGMA integrity_check;"

# Restore
sudo cp /tmp/restored.db /opt/stock-market-words/data/market_data.db
sudo chown smw:smw /opt/stock-market-words/data/market_data.db
```

## Consequences

**Positive:**
- Off-site backup for ~$0.05/mo
- Least-privilege IAM: ThinkPad can only write to one bucket prefix
- 30-day rolling window provides ample recovery options
- Automated via systemd — zero manual effort after setup

**Negative:**
- Requires AWS account setup (one-time)
- Access keys on the ThinkPad are a credential to manage (rotate every 90 days)
- Single-AZ storage: ~0.1% annual data loss risk (acceptable for backups with 30-day depth)

**Neutral:**
- No delete permissions: old backups expire via lifecycle, not by the ThinkPad
- Restore is manual (by design — don't automate destructive operations)
