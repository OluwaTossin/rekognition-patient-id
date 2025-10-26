import pytest
import json
import base64
import boto3
from moto import mock_rekognition, mock_dynamodb
from unittest.mock import patch, MagicMock
import sys
import os

# Add the build-register directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build-register'))

from register_patient import handler


@mock_rekognition
@mock_dynamodb
class TestRegisterPatient:
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create mock AWS services
        self.rekognition = boto3.client('rekognition', region_name='us-east-1')
        self.dynamodb = boto3.client('dynamodb', region_name='us-east-1')
        
        # Create Rekognition collection
        self.rekognition.create_collection(CollectionId='test-collection')
        
        # Create DynamoDB table
        self.dynamodb.create_table(
            TableName='test-table',
            KeySchema=[
                {'AttributeName': 'patient_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'patient_id', 'AttributeType': 'S'},
                {'AttributeName': 'face_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'face_id-index',
                    'KeySchema': [
                        {'AttributeName': 'face_id', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
    
    @patch.dict(os.environ, {
        'COLLECTION_ID': 'test-collection',
        'TABLE_NAME': 'test-table'
    })
    def test_successful_registration(self):
        """Test successful patient registration."""
        # Create a simple test image (1x1 pixel PNG)
        test_image = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0fIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82').decode()
        
        event = {
            "body": json.dumps({
                "patient_id": "P-TEST-001",
                "image_base64": test_image,
                "attributes": {
                    "name": "Test Patient",
                    "dob": "1990-01-01",
                    "phone": "+1234567890"
                }
            })
        }
        
        # Mock the Rekognition response
        with patch('register_patient.reko') as mock_reko:
            mock_reko.index_faces.return_value = {
                'FaceRecords': [
                    {
                        'Face': {
                            'FaceId': 'test-face-id-12345',
                            'BoundingBox': {
                                'Width': 0.5,
                                'Height': 0.5,
                                'Left': 0.25,
                                'Top': 0.25
                            },
                            'Confidence': 99.5
                        }
                    }
                ]
            }
            
            # Mock DynamoDB
            with patch('register_patient.ddb') as mock_ddb:
                mock_ddb.put_item.return_value = {}
                
                response = handler(event, {})
                
                assert response['statusCode'] == 201
                body = json.loads(response['body'])
                assert body['patient_id'] == 'P-TEST-001'
                assert body['face_id'] == 'test-face-id-12345'
    
    @patch.dict(os.environ, {
        'COLLECTION_ID': 'test-collection',
        'TABLE_NAME': 'test-table'
    })
    def test_no_face_detected(self):
        """Test registration with no face detected."""
        test_image = base64.b64encode(b'fake_image_data').decode()
        
        event = {
            "body": json.dumps({
                "patient_id": "P-TEST-002",
                "image_base64": test_image,
                "attributes": {
                    "name": "Test Patient 2"
                }
            })
        }
        
        # Mock Rekognition to return no faces
        with patch('register_patient.reko') as mock_reko:
            mock_reko.index_faces.return_value = {'FaceRecords': []}
            
            response = handler(event, {})
            
            assert response['statusCode'] == 422
            body = json.loads(response['body'])
            assert 'No face detected' in body['message']
    
    @patch.dict(os.environ, {
        'COLLECTION_ID': 'test-collection',
        'TABLE_NAME': 'test-table'
    })
    def test_invalid_json(self):
        """Test registration with invalid JSON."""
        event = {
            "body": "invalid json"
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
    
    @patch.dict(os.environ, {
        'COLLECTION_ID': 'test-collection',
        'TABLE_NAME': 'test-table'
    })
    def test_missing_required_fields(self):
        """Test registration with missing required fields."""
        event = {
            "body": json.dumps({
                "patient_id": "P-TEST-003"
                # Missing image_base64
            })
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body