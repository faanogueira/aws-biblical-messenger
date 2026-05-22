"""
Client example for using the Biblical Messages API.
"""

import requests
import json
from typing import Dict, Optional

class BiblicalMessagesClient:
    """Client for Biblical Messages API."""
    
    def __init__(self, api_endpoint: str):
        """
        Initialize the client.
        
        Args:
            api_endpoint: Base URL of the API (e.g., https://xxx.execute-api.region.amazonaws.com/dev)
        """
        self.api_endpoint = api_endpoint
        self.session = requests.Session()
    
    def generate_message(
        self,
        theme: str,
        style: str = 'reflection',
        user_id: str = 'anonymous'
    ) -> Dict:
        """
        Generate a biblical message.
        
        Args:
            theme: Message theme (faith, hope, love, etc.)
            style: Writing style (reflection, prayer, story, etc.)
            user_id: User identifier
        
        Returns:
            API response with generated message
        """
        
        url = f"{self.api_endpoint}/generate"
        
        payload = {
            'theme': theme,
            'style': style,
            'user_id': user_id
        }
        
        try:
            response = self.session.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def batch_generate(
        self,
        themes: list,
        style: str = 'reflection',
        user_id: str = 'anonymous'
    ) -> Dict:
        """Generate messages for multiple themes."""
        
        results = {}
        for theme in themes:
            results[theme] = self.generate_message(theme, style, user_id)
        
        return results

# Usage example
if __name__ == '__main__':
    # Initialize client
    client = BiblicalMessagesClient(
        api_endpoint='https://xxx.execute-api.us-east-1.amazonaws.com/dev'
    )
    
    # Generate single message
    response = client.generate_message(
        theme='faith',
        style='reflection',
        user_id='user_123'
    )
    
    if response.get('success'):
        print("Generated Message:")
        print(response['data']['message'])
        print(f"\nTheme: {response['data']['theme']}")
        print(f"Style: {response['data']['style']}")
    else:
        print(f"Error: {response.get('error')}")
    
    # Generate multiple messages
    themes = ['faith', 'hope', 'love', 'forgiveness']
    batch_results = client.batch_generate(
        themes=themes,
        style='prayer'
    )
    
    for theme, result in batch_results.items():
        if result.get('success'):
            print(f"\n{theme.upper()}:")
            print(result['data']['message'][:100] + "...")