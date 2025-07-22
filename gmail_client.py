import os
import json
import base64
import email
from typing import List, Dict, Optional
from datetime import datetime, timezone
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GmailClient:
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        """
        Initialize Gmail client with OAuth 2.0
        
        Args:
            credentials_file: Path to OAuth 2.0 credentials JSON file
            token_file: Path to store/load access tokens
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.my_email = None
        
    async def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth 2.0"""
        try:
            creds = None
            
            # Load existing token
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
                
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Refreshing expired token...")
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        logger.error(f"Credentials file {self.credentials_file} not found!")
                        logger.info("Please download OAuth 2.0 credentials from Google Cloud Console")
                        return False
                        
                    logger.info("Starting OAuth 2.0 flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                    
                # Save credentials for next run
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                    
            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=creds)
            
            # Get user email address
            profile = self.service.users().getProfile(userId='me').execute()
            self.my_email = profile['emailAddress']
            
            logger.info(f"✅ Successfully authenticated as {self.my_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {str(e)}")
            return False
    
    def send_email(self, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> Dict:
        """
        Send email via Gmail API
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            thread_id: Optional Gmail thread ID for replies
            
        Returns:
            Dict with email details or error info
        """
        try:
            # Create message
            message_text = f"""To: {to}
From: {self.my_email}
Subject: {subject}

{body}"""
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message_text.encode('utf-8')).decode('utf-8')
            
            message_body = {'raw': raw_message}
            if thread_id:
                message_body['threadId'] = thread_id
                
            # Send email
            result = self.service.users().messages().send(
                userId='me', 
                body=message_body
            ).execute()
            
            sent_time = datetime.now(timezone.utc)
            
            logger.info(f"📧 EMAIL SENT to {to}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Time: {sent_time.strftime('%H:%M:%S')}")
            logger.info(f"   Message ID: {result['id']}")
            
            return {
                'success': True,
                'message_id': result['id'],
                'thread_id': result.get('threadId'),
                'timestamp': sent_time,
                'to': to,
                'subject': subject,
                'body': body
            }
            
        except HttpError as e:
            logger.error(f"❌ Failed to send email: {str(e)}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"❌ Unexpected error sending email: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_new_emails(self, from_email: str, since_timestamp: Optional[datetime] = None, since_message_id: Optional[str] = None) -> List[Dict]:
        """
        Get new emails from specific sender

        Args:
            from_email: Email address to check for messages from
            since_timestamp: Only get emails after this timestamp
            since_message_id: Only get emails after this message ID

        Returns:
            List of email dictionaries
        """
        try:
            # Build query
            query = f'from:{from_email}'

            # Add timestamp filter if provided
            if since_timestamp:
                # Convert to Gmail query format (seconds since epoch)
                epoch_time = int(since_timestamp.timestamp())
                query += f' after:{epoch_time}'

            # Search for messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=10
            ).execute()

            messages = results.get('messages', [])

            # Get full message details
            emails = []
            for msg in messages:
                try:
                    full_msg = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()

                    # Parse email
                    parsed_email = self._parse_gmail_message(full_msg)
                    if parsed_email:
                        # Additional timestamp filter if needed
                        if since_timestamp and parsed_email['timestamp'] <= since_timestamp:
                            continue
                        emails.append(parsed_email)

                except Exception as e:
                    logger.error(f"Error parsing message {msg['id']}: {str(e)}")
                    continue

            # Sort by timestamp (newest first)
            emails.sort(key=lambda x: x['timestamp'], reverse=True)

            if emails:
                logger.info(f"📬 Found {len(emails)} email(s) from {from_email}")
                for email_data in emails:
                    logger.info(f"   - {email_data['subject']} at {email_data['timestamp'].strftime('%H:%M:%S')}")

            return emails

        except Exception as e:
            logger.error(f"❌ Error checking emails: {str(e)}")
            return []
    
    def _parse_gmail_message(self, message: Dict) -> Optional[Dict]:
        """Parse Gmail API message format into our email structure"""
        try:
            headers = message['payload']['headers']
            
            # Extract headers
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Parse timestamp
            if date_str:
                # Gmail provides timestamp in milliseconds
                timestamp = datetime.fromtimestamp(
                    int(message['internalDate']) / 1000,
                    tz=timezone.utc
                )
            else:
                timestamp = datetime.now(timezone.utc)
                
            # Extract body
            body = self._extract_email_body(message['payload'])
            
            return {
                'id': message['id'],
                'thread_id': message['threadId'],
                'subject': subject,
                'from': from_email,
                'body': body,
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"Error parsing message: {str(e)}")
            return None
    
    def _extract_email_body(self, payload: Dict) -> str:
        """Extract body text from Gmail message payload"""
        try:
            if 'parts' in payload:
                # Multipart message
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        return base64.urlsafe_b64decode(data).decode('utf-8')
            else:
                # Single part message
                if payload['mimeType'] == 'text/plain':
                    data = payload['body']['data']
                    return base64.urlsafe_b64decode(data).decode('utf-8')
                    
            return "Could not extract email body"
            
        except Exception as e:
            logger.error(f"Error extracting email body: {str(e)}")
            return "Error extracting email body"
