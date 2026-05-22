import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError
from config import SYSTEM_PROMPT, MODEL_ID

# Initialize Bedrock client
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# DynamoDB table for logging
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'BiblicalMessages')

def lambda_handler(event, context):
    """
    Main Lambda handler for generating biblical messages.
    
    Expected event:
    {
        "theme": "faith",
        "style": "reflection",
        "user_id": "user123"
    }
    """
    
    try:
        # Parse request
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event
        
        theme = body.get('theme', 'faith')
        style = body.get('style', 'reflection')
        user_id = body.get('user_id', 'anonymous')
        
        # Validate inputs
        if not theme or not isinstance(theme, str):
            return error_response("Invalid theme parameter", 400)
        
        # Generate message
        message = generate_biblical_message(theme, style)
        
        if not message:
            return error_response("Failed to generate message", 500)
        
        # Log to DynamoDB
        log_message(user_id, theme, style, message)
        
        # Return success response
        return success_response({
            'message': message,
            'theme': theme,
            'style': style,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id
        })
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(f"Internal server error: {str(e)}", 500)

def generate_biblical_message(theme: str, style: str) -> str:
    """
    Generate a biblical message using Claude 3 via Bedrock.
    
    Args:
        theme: Topic for the message (e.g., 'faith', 'hope', 'love')
        style: Writing style (e.g., 'reflection', 'prayer', 'story')
    
    Returns:
        Generated biblical message in Portuguese
    """
    
    user_prompt = create_prompt(theme, style)
    
    try:
        response = bedrock_runtime.converse(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            system=SYSTEM_PROMPT,
            inferenceConfig={
                "maxTokens": 500,
                "temperature": 0.7,
                "topP": 0.9
            }
        )
        
        # Extract text from response
        message_content = response['output']['message']['content'][0]['text']
        return message_content
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ValidationException':
            print(f"Validation error with Bedrock: {e}")
        elif error_code == 'ThrottlingException':
            print(f"Request throttled: {e}")
        else:
            print(f"Bedrock error: {e}")
        raise

def create_prompt(theme: str, style: str) -> str:
    """Create a detailed prompt for message generation."""
    
    style_descriptions = {
        'reflection': 'uma reflexão profunda e meditativa',
        'prayer': 'uma oração sincera e tocante',
        'story': 'uma história ou parábola inspiradora',
        'verse': 'um verso bíblico com interpretação',
        'daily': 'uma mensagem para o dia'
    }
    
    style_desc = style_descriptions.get(style, 'uma reflexão profunda e meditativa')
    
    prompt = f"""Gere {style_desc} sobre o tema "{theme}".

Requisitos:
- Máximo 300 palavras
- Tom inspirador e reconfortante
- Incluir referências bíblicas quando apropriado
- Linguagem clara e acessível em português
- Acabar com uma mensagem de esperança

Tema: {theme}
Estilo: {style}"""
    
    return prompt

def log_message(user_id: str, theme: str, style: str, message: str) -> None:
    """
    Log the generated message to DynamoDB.
    """
    
    try:
        table = dynamodb.Table(TABLE_NAME)
        
        table.put_item(
            Item={
                'message_id': f"{user_id}#{datetime.utcnow().isoformat()}",
                'user_id': user_id,
                'theme': theme,
                'style': style,
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'character_count': len(message),
                'ttl': int(datetime.utcnow().timestamp()) + (90 * 24 * 60 * 60)  # 90 days
            }
        )
        
    except ClientError as e:
        print(f"Error logging to DynamoDB: {e}")
        # Don't raise - logging failure shouldn't break the main function

def success_response(data: dict) -> dict:
    """Format a successful response."""
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'success': True,
            'data': data
        })
    }

def error_response(message: str, status_code: int = 500) -> dict:
    """Format an error response."""
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'success': False,
            'error': message
        })
    }