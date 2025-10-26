import pytest
import json
import base64
import boto3
from moto import mock_rekognition, mock_dynamodb
from unittest.mock import patch, MagicMock
import sys
import os

# Add the build-identify directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build-identify'))

from identify_patient import handler


@mock_rekognition
@mock_dynamodb
class TestIdentifyPatient:
    
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
        'TABLE_NAME': 'test-table',
        'MATCH_THRESHOLD': '95'
    })
    def test_successful_identification(self):
        """Test successful patient identification."""
        test_image = base64.b64encode(b'fake_image_data').decode()
        
        event = {
            "body": json.dumps({
                "image_base64": test_image
            })
        }
        
        # Mock Rekognition response
        with patch('identify_patient.reko') as mock_reko:
            mock_reko.search_faces_by_image.return_value = {
                'FaceMatches': [
                    {
                        'Face': {
                            'FaceId': 'test-face-id-12345'
                        },
                        'Similarity': 97.5
                    }
                ]
            }
            
            # Mock DynamoDB response
            with patch('identify_patient.ddb') as mock_ddb:
                mock_ddb.query.return_value = {
                    'Items': [
                        {
                            'patient_id': {'S': 'P-TEST-001'},
                            'face_id': {'S': 'test-face-id-12345'},
                            'name': {'S': 'Test Patient'},
                            'dob': {'S': '1990-01-01'},
                            'phone': {'S': '+1234567890'}
                        }
                    ]
                }
                
                response = handler(event, {})
                
                assert response['statusCode'] == 200
                body = json.loads(response['body'])
                assert body['patient_id'] == 'P-TEST-001'
                assert body['name'] == 'Test Patient'
                assert body['similarity'] == 97.5
    
    @patch.dict(os.environ, {
        'COLLECTION_ID': 'test-collection',
        'TABLE_NAME': 'test-table',
        'MATCH_THRESHOLD': '95'
    })
    def test_no_face_match(self):
        """Test identification with no face match."""
        test_image = base64.b64encode(b'fake_image_data').decode()
        
        event = {
            "body": json.dumps({
                "image_base64": test_image
            })
        }
        
        # Mock Rekognition to return no matches
        with patch('identify_patient.reko') as mock_reko:
            mock_reko.search_faces_by_image.return_value = {'FaceMatches': []}
            
            response = handler(event, {})
            
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert 'No confident match' in body['message']
    
    @patch.dict(os.environ, {
        'COLLECTION_ID': 'test-collection',
        'TABLE_NAME': 'test-table',
        'MATCH_THRESHOLD': '95'
    })
    def test_face_match_no_patient_record(self):
        """Test identification with face match but no patient record."""
        test_image = base64.b64encode(b'fake_image_data').decode()
        
        event = {
            "body": json.dumps({
                "image_base64": test_image
            })
        }
        
        # Mock Rekognition response with match
        with patch('identify_patient.reko') as mock_reko:
            mock_reko.search_faces_by_image.return_value = {
                'FaceMatches': [
                    {
                        'Face': {
                            'FaceId': 'test-face-id-12345'
                        },
                        'Similarity': 97.5
                    }
                ]
            }
            
            # Mock DynamoDB to return no items
            with patch('identify_patient.ddb') as mock_ddb:
                mock_ddb.query.return_value = {'Items': []}
                
                response = handler(event, {})
                
                assert response['statusCode'] == 404
                body = json.loads(response['body'])
                assert 'Face mapped but no patient record' in body['message']
    
    @patch.dict(os.environ, {
        'COLLECTION_ID': 'test-collection',
        'TABLE_NAME': 'test-table',
        'MATCH_THRESHOLD': '95'
    })
    def test_invalid_base64_image(self):
        """Test identification with invalid base64 image."""
        event = {
            "body": json.dumps({
                "image_base64": "invalid_base64_data"
            })
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
    
    @patch.dict(os.environ, {
        'COLLECTION_ID': 'test-collection',
        'TABLE_NAME': 'test-table',
        'MATCH_THRESHOLD': '95'
    })
    def test_missing_image_field(self):
        """Test identification with missing image field."""
        event = {
            "body": json.dumps({})
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body