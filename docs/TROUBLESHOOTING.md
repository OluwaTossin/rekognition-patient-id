# Troubleshooting Guide

## Common Issues

### 1. "No face detected" Error (422)

**Symptoms:**
- Patient registration fails with 422 status code
- Error message: "No face detected or poor quality"

**Causes:**
- Poor image quality (blurry, dark, low resolution)
- Face not clearly visible (sunglasses, mask, extreme angle)
- Multiple faces in image
- Image format not supported

**Solutions:**
```python
# Add image validation before processing
def validate_image_quality(image_bytes):
    response = rekognition.detect_faces(
        Image={'Bytes': image_bytes},
        Attributes=['ALL']
    )
    
    if not response['FaceDetails']:
        raise ValueError("No face detected")
    
    face = response['FaceDetails'][0]
    if face['Confidence'] < 90:
        raise ValueError("Face detection confidence too low")
    
    return True
```

**Best Practices:**
- Use images with resolution ≥ 640x480
- Ensure good lighting conditions
- Face should occupy at least 50% of image
- Avoid sunglasses, masks, or extreme angles

### 2. High Lambda Cold Start Times

**Symptoms:**
- Initial API responses take >3 seconds
- Subsequent requests are much faster

**Solutions:**
```python
# Optimize imports - move outside handler when possible
import boto3
import json
import base64

# Initialize clients outside handler
rekognition = boto3.client('rekognition')
dynamodb = boto3.client('dynamodb')

def handler(event, context):
    # Handler code here
    pass
```

**Performance Optimizations:**
- Enable Lambda Provisioned Concurrency for consistent traffic
- Use Lambda layers for shared dependencies
- Minimize package size
- Use connection pooling for database connections

### 3. DynamoDB Throttling (400 Error)

**Symptoms:**
- ProvisionedThroughputExceededException
- Intermittent 400 errors during high traffic

**Solutions:**
```python
import time
import random

def exponential_backoff_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait_time)
                    continue
            raise
    
# Usage
exponential_backoff_retry(lambda: ddb.put_item(TableName=TABLE_NAME, Item=item))
```

**Long-term Solutions:**
- Switch to DynamoDB On-Demand billing
- Increase provisioned capacity
- Implement application-level caching

### 4. Rekognition Collection Limits

**Symptoms:**
- ResourceLimitExceededException when registering patients
- Collection approaching 20M face limit

**Solutions:**
```python
def check_collection_size():
    response = rekognition.describe_collection(CollectionId=COLLECTION_ID)
    face_count = response['FaceCount']
    
    if face_count > 19000000:  # 19M faces
        logger.warning(f"Collection approaching limit: {face_count} faces")
        # Implement archival or rotation strategy
        
    return face_count
```

**Mitigation Strategies:**
- Implement face collection rotation
- Archive inactive patients to separate collection
- Use multiple collections with load balancing

### 5. Base64 Decoding Errors

**Symptoms:**
- Invalid base64 image data errors
- Image processing failures

**Solutions:**
```python
import base64
from PIL import Image
import io

def validate_and_process_image(image_b64):
    try:
        # Decode base64
        image_data = base64.b64decode(image_b64)
        
        # Validate image format
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Save back to bytes
        output = io.BytesIO()
        image.save(output, format='JPEG')
        return output.getvalue()
        
    except Exception as e:
        raise ValueError(f"Invalid image data: {str(e)}")
```

### 6. API Gateway Timeout (504)

**Symptoms:**
- 504 Gateway Timeout errors
- Lambda function times out after 29 seconds

**Solutions:**
```python
# Set appropriate Lambda timeout
aws lambda update-function-configuration \
  --function-name register-patient \
  --timeout 30

# Optimize function performance
def handler(event, context):
    # Add timeout handling
    remaining_time = context.get_remaining_time_in_millis()
    
    if remaining_time < 5000:  # Less than 5 seconds remaining
        return {
            'statusCode': 503,
            'body': json.dumps({'error': 'Request timeout'})
        }
```

## Debug Mode

### Enable Detailed Logging
```python
import logging
import os

# Set log level from environment
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logger = logging.getLogger()
logger.setLevel(getattr(logging, log_level))

def handler(event, context):
    logger.debug(f"Received event: {json.dumps(event)}")
    
    try:
        # Your code here
        result = process_request(event)
        logger.info(f"Processing successful: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}", exc_info=True)
        raise
```

### Health Check Endpoint
```python
def health_check(event, context):
    """Comprehensive health check"""
    health_status = {
        'status': 'healthy',
        'timestamp': int(time.time() * 1000),
        'services': {}
    }
    
    try:
        # Test DynamoDB
        ddb.describe_table(TableName=TABLE_NAME)
        health_status['services']['dynamodb'] = 'ok'
    except Exception as e:
        health_status['services']['dynamodb'] = f'error: {str(e)}'
        health_status['status'] = 'degraded'
    
    try:
        # Test Rekognition
        reko.describe_collection(CollectionId=COLLECTION_ID)
        health_status['services']['rekognition'] = 'ok'
    except Exception as e:
        health_status['services']['rekognition'] = f'error: {str(e)}'
        health_status['status'] = 'degraded'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(health_status)
    }
```

## Monitoring and Alerting

### CloudWatch Alarms
```bash
# High error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "HighErrorRate-RegisterPatient" \
  --alarm-description "High error rate for patient registration" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=register-patient \
  --evaluation-periods 2

# High latency alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "HighLatency-IdentifyPatient" \
  --alarm-description "High latency for patient identification" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Average \
  --period 300 \
  --threshold 5000 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=identify-patient \
  --evaluation-periods 1
```

### Custom Metrics
```python
def publish_custom_metrics(similarity_score, processing_time):
    cloudwatch = boto3.client('cloudwatch')
    
    # Publish similarity score
    cloudwatch.put_metric_data(
        Namespace='PatientIdentity',
        MetricData=[
            {
                'MetricName': 'IdentificationAccuracy',
                'Value': similarity_score,
                'Unit': 'Percent',
                'Dimensions': [
                    {
                        'Name': 'Environment',
                        'Value': os.environ.get('ENVIRONMENT', 'dev')
                    }
                ]
            },
            {
                'MetricName': 'ProcessingTime',
                'Value': processing_time,
                'Unit': 'Milliseconds'
            }
        ]
    )
```

## Performance Optimization

### Image Processing
```python
def optimize_image_for_rekognition(image_bytes, max_size=5*1024*1024):
    """Optimize image for Rekognition processing"""
    from PIL import Image
    import io
    
    # Check size
    if len(image_bytes) <= max_size:
        return image_bytes
    
    # Compress image
    image = Image.open(io.BytesIO(image_bytes))
    
    # Calculate new dimensions
    quality = 85
    while True:
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=quality, optimize=True)
        
        if len(output.getvalue()) <= max_size or quality <= 30:
            return output.getvalue()
        
        quality -= 10
```

### Connection Pooling
```python
import boto3
from botocore.config import Config

# Configure connection pooling
config = Config(
    max_pool_connections=50,
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'
    }
)

rekognition = boto3.client('rekognition', config=config)
dynamodb = boto3.client('dynamodb', config=config)
```

## Getting Help

### Log Analysis
```bash
# Search CloudWatch logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/register-patient \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"

# Get recent errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/identify-patient \
  --start-time $(date -d '10 minutes ago' +%s)000 \
  --filter-pattern "Exception"
```

### Support Channels
- GitHub Issues: Report bugs and feature requests
- AWS Support: For service-specific issues
- Community Forums: For general questions and discussions

### Emergency Procedures
1. **Service Degradation**: Check AWS Service Health Dashboard
2. **High Error Rates**: Review recent deployments and rollback if necessary
3. **Data Issues**: Enable detailed logging and contact support
4. **Security Incidents**: Follow incident response procedures in SECURITY.md