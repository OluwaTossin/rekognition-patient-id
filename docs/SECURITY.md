# Security & Compliance Guide

## Data Protection

### Encryption
- **At Rest**: DynamoDB tables encrypted with AWS KMS
- **In Transit**: All API calls use HTTPS/TLS 1.2+
- **Images**: Base64 images processed in memory only, never stored permanently

### Access Control
- **IAM Least Privilege**: Lambda functions have minimal required permissions
- **API Gateway**: Rate limiting, request validation, and authentication
- **VPC Deployment**: Optional isolation for enhanced security

## HIPAA Compliance

### Requirements
- **Business Associate Agreement (BAA)** with AWS
- **Data Minimization**: Store only essential patient information
- **Access Logging**: Comprehensive audit trail for all data access
- **Data Retention**: Configurable retention policies

### Implementation
```python
# Example: Audit logging in Lambda
import json
import time

def log_patient_access(patient_id, action, user_id=None):
    audit_record = {
        'timestamp': int(time.time() * 1000),
        'patient_id': patient_id,
        'action': action,
        'user_id': user_id or 'system',
        'ip_address': get_client_ip(),
        'user_agent': get_user_agent()
    }
    
    # Log to CloudWatch for compliance
    logger.info(f"AUDIT: {json.dumps(audit_record)}")
```

### Data Subject Rights (GDPR)
- **Right to Access**: Patient data export functionality
- **Right to Deletion**: Secure data deletion from all systems
- **Right to Portability**: Standard data format for transfers
- **Consent Management**: Tracking and withdrawal of biometric consent

## Best Practices

### Development
- Use environment variables for sensitive configuration
- Implement proper error handling without exposing sensitive data
- Regular security scanning with tools like `bandit`
- Code reviews for security-sensitive changes

### Operations
- Regular access reviews and permission audits
- Monitoring and alerting for unusual access patterns
- Backup and disaster recovery procedures
- Incident response planning