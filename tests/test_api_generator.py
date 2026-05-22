import json
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch, MagicMock
import sys
import os

# Add lambda to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src/lambda_api_generator'))

# Set mock AWS environment variables before any imports to avoid boto3 credentials check
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

from generate_message import (
    lambda_handler,
    generate_biblical_message,
    create_prompt,
    success_response,
    error_response
)

@pytest.fixture
def valid_event():
    """Create a valid event for testing."""
    return {
        'body': json.dumps({
            'theme': 'faith',
            'style': 'reflection',
            'user_id': 'test_user_123'
        })
    }

def test_create_prompt():
    """Test prompt creation."""
    prompt = create_prompt('faith', 'reflection')
    
    assert 'faith' in prompt.lower()
    assert 'reflexão' in prompt.lower() or 'reflection' in prompt.lower()
    assert len(prompt) > 50

def test_success_response():
    """Test success response format."""
    data = {'message': 'Test message', 'theme': 'faith'}
    response = success_response(data)
    
    assert response['statusCode'] == 200
    assert 'body' in response
    assert response['headers']['Content-Type'] == 'application/json'
    
    body = json.loads(response['body'])
    assert body['success'] is True
    assert body['data'] == data

def test_error_response():
    """Test error response format."""
    response = error_response('Test error', 400)
    
    assert response['statusCode'] == 400
    assert 'body' in response
    
    body = json.loads(response['body'])
    assert body['success'] is False
    assert body['error'] == 'Test error'

def test_lambda_handler_invalid_json():
    """Test handler with invalid JSON."""
    event = {
        'body': 'invalid json {{'
    }
    
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['success'] is False

@mock_aws
def test_lambda_handler_missing_theme():
    """Test handler with missing theme."""
    event = {
        'body': json.dumps({
            'style': 'reflection',
            'user_id': 'test_user'
        })
    }
    
    # Should use default theme
    with patch('generate_message.bedrock_runtime') as mock_bedrock:
        mock_bedrock.converse.return_value = {
            'output': {
                'message': {
                    'content': [{'text': 'Generated message'}]
                }
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200

@mock_aws
def test_lambda_handler_with_dynamodb():
    """Test handler with DynamoDB logging."""
    # Create table
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='BiblicalMessages',
        KeySchema=[{'AttributeName': 'message_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'message_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    
    event = {
        'body': json.dumps({
            'theme': 'faith',
            'style': 'reflection',
            'user_id': 'test_user'
        })
    }
    
    with patch('generate_message.bedrock_runtime') as mock_bedrock:
        mock_bedrock.converse.return_value = {
            'output': {
                'message': {
                    'content': [{'text': 'Generated biblical message'}]
                }
            }
        }
        
        with patch.dict(os.environ, {'DYNAMODB_TABLE': 'BiblicalMessages'}):
            response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200

class TestIntegration:
    """Integration tests for the Lambda function."""
    
    @mock_aws
    @patch('generate_message.bedrock_runtime')
    def test_full_workflow(self, mock_bedrock):
        """Test complete workflow."""
        # Mock Bedrock response
        mock_bedrock.converse.return_value = {
            'output': {
                'message': {
                    'content': [{
                        'text': 'Uma mensagem bíblica inspiradora sobre fé...'
                    }]
                }
            }
        }
        
        event = {
            'body': json.dumps({
                'theme': 'faith',
                'style': 'reflection',
                'user_id': 'user_123'
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'message' in body['data']
        assert body['data']['theme'] == 'faith'
        assert body['data']['style'] == 'reflection'

if __name__ == '__main__':
    pytest.main([__file__, '-v'])