import asyncio
import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import re

from langchain_google_genai import ChatGoogleGenerativeAI
from gmail_client import GmailClient
from state_manager import StateManager

logger = logging.getLogger(__name__)

class InteractiveClientAgent:
    def __init__(self, persona_type: str, wandero_email: str, company_info: Dict, 
                 google_api_key: str, gmail_credentials_file: str = 'credentials.json',
                 test_mode: bool = False):
        """
        Initialize Interactive Client Agent
        
        Args:
            persona_type: Type of client persona to simulate
            wandero_email: Email address of Wandero agent
            company_info: Information about the travel company
            google_api_key: Google API key for Gemini
            gmail_credentials_file: Path to Gmail OAuth credentials
            test_mode: If True, responds immediately for testing. If False, uses realistic timing
        """
        self.persona_type = persona_type
        self.wandero_email = wandero_email
        self.company_info = company_info
        self.test_mode = test_mode  # Add this line
        
        # Initialize components
        self.gmail_client = GmailClient(gmail_credentials_file)
        self.state_manager = StateManager(persona_type, wandero_email)
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=google_api_key
        )
        
        # Get persona data
        self.persona_data = self.state_manager.get_state()['persona_data']
        self.client_name = self.persona_data['name']
        
        mode_text = "TEST MODE (immediate responses)" if test_mode else "DEMO MODE (realistic timing)"
        logger.info(f"[AGENT] Interactive Client Agent initialized - {mode_text}")
        logger.info(f"   Persona: {self.client_name} ({persona_type})")
        logger.info(f"   Wandero: {wandero_email}")
        logger.info(f"   Company: {company_info.get('name', 'Unknown')}")
    
    async def start_conversation(self):
        """Start the conversation by sending initial inquiry"""
        try:
            # Authenticate with Gmail
            auth_success = await self.gmail_client.authenticate()
            if not auth_success:
                logger.error("❌ Gmail authentication failed. Cannot start conversation.")
                return False
            
            logger.info(f"🚀 Starting conversation as {self.client_name}")
            
            # Check if conversation already started
            state = self.state_manager.get_state()
            if state['messages']:
                logger.info(f"📋 Resuming existing conversation ({len(state['messages'])} messages)")
                return await self.resume_conversation()
            else:
                logger.info("📧 Sending initial inquiry...")
                return await self.send_initial_inquiry()
                
        except Exception as e:
            logger.error(f"❌ Error starting conversation: {str(e)}")
            return False
    
    async def send_initial_inquiry(self) -> bool:
        """Send the first email to Wandero"""
        try:
            # Generate initial inquiry using persona
            subject, body = await self.generate_initial_inquiry()
            
            # Send email
            result = self.gmail_client.send_email(
                to=self.wandero_email,
                subject=subject,
                body=body
            )
            
            if result['success']:
                # Add to conversation history
                message = {
                    'id': result['message_id'],
                    'thread_id': result['thread_id'],
                    'subject': subject,
                    'body': body,
                    'sender': self.client_name,
                    'timestamp': result['timestamp']
                }
                
                self.state_manager.add_message(message)
                self.state_manager.update_phase('information_gathering')
                
                logger.info("✅ Initial inquiry sent successfully!")
                return True
            else:
                logger.error(f"❌ Failed to send initial inquiry: {result['error']}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending initial inquiry: {str(e)}")
            return False
    
    async def resume_conversation(self) -> bool:
        """Resume an existing conversation"""
        logger.info("🔄 Resuming conversation...")
        return True
    
    async def run_conversation_loop(self):
        """Main conversation loop - monitors for Wandero responses and replies"""
        logger.info("👀 Starting conversation monitoring...")
        logger.info("   Checking for new emails every 30 seconds...")
        logger.info("   Press Ctrl+C to stop")
        
        try:
            check_count = 0
            while not self.state_manager.is_conversation_ended():
                check_count += 1
                
                # Check for new emails from Wandero
                new_emails = self.gmail_client.get_new_emails(self.wandero_email)
                
                # Filter out already processed emails
                state = self.state_manager.get_state()
                last_processed_id = self.state_manager.get_last_processed_message_id()
                
                unprocessed_emails = []
                for email in new_emails:
                    # Simple check: if we haven't seen this email before
                    already_processed = any(
                        msg.get('id') == email['id'] 
                        for msg in state['messages']
                    )
                    if not already_processed:
                        unprocessed_emails.append(email)
                
                if unprocessed_emails:
                    logger.info(f"📬 Processing {len(unprocessed_emails)} new email(s)...")
                    
                    for email in unprocessed_emails:
                        await self.process_wandero_email(email)
                        
                        # Mark as processed
                        self.state_manager.set_last_processed_message_id(email['id'])
                        
                        # Generate and send response
                        await self.generate_and_send_response(email)
                        
                        # Small delay between processing emails
                        await asyncio.sleep(2)
                
                else:
                    # No new emails
                    if check_count % 10 == 0:  # Log every 5 minutes (10 * 30 seconds)
                        logger.info(f"⏱️  Still waiting for response from Wandero... (checked {check_count} times)")
                
                # Wait before next check
                await asyncio.sleep(30)
                
        except KeyboardInterrupt:
            logger.info("\n👋 Conversation monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Error in conversation loop: {str(e)}")
    
    async def process_wandero_email(self, email: Dict):
        """Process incoming email from Wandero"""
        logger.info(f"📖 Processing email from Wandero:")
        logger.info(f"   Subject: {email['subject']}")
        logger.info(f"   Received: {email['timestamp'].strftime('%H:%M:%S')}")
        
        # Add to conversation history
        message = {
            'id': email['id'],
            'thread_id': email['thread_id'],
            'subject': email['subject'],
            'body': email['body'],
            'sender': f"Wandero Agent <{self.wandero_email}>",
            'timestamp': email['timestamp']
        }
        
        self.state_manager.add_message(message)
        
        # Analyze email content and update conversation phase
        await self.analyze_wandero_email(email)
        
        # Track Wandero response time
        state = self.state_manager.get_state()
        if state.get('last_client_response'):
            response_time_minutes = (
                email['timestamp'] - state['last_client_response']
            ).total_seconds() / 60
            
            state['wandero_response_times'].append(response_time_minutes)
            logger.info(f"⏱️  Wandero responded in {response_time_minutes:.1f} minutes")
    
    async def analyze_wandero_email(self, email: Dict):
        """Analyze Wandero's email to understand context and update state"""
        try:
            analysis_prompt = f"""
            Analyze this email from a travel agency to understand what they're asking for:
            
            Subject: {email['subject']}
            Body: {email['body']}
            
            Determine:
            1. What information are they requesting? (budget, dates, group size, interests, etc.)
            2. Are they presenting a proposal or quote?
            3. What is the overall tone? (friendly, formal, pushy, helpful)
            4. What phase of conversation is this? (introduction, information gathering, proposal, negotiation)
            
            Current client personality: {self.persona_data.get('personality', 'standard')}
            
            Return analysis as JSON with keys: requesting_info, has_proposal, tone, suggested_phase, key_points
            """
            
            response = self.llm.invoke(analysis_prompt)
            
            # Simple parsing - in production would use structured output
            email_content = email['body'].lower()
            
            # Update conversation phase based on content
            if any(word in email_content for word in ['welcome', 'hello', 'introduction']):
                if not self.state_manager.get_state()['messages']:
                    self.state_manager.update_phase('information_gathering')
            elif any(phrase in email_content for phrase in ['proposal', 'quote', '$', 'price', 'itinerary']):
                self.state_manager.update_phase('proposal_review')
            elif any(word in email_content for word in ['discount', 'negotiate', 'flexible', 'adjust']):
                self.state_manager.update_phase('negotiation')
            
            # Update interest level based on tone/content
            current_interest = self.state_manager.get_state()['interest_level']
            
            # Simple sentiment analysis
            positive_words = ['exciting', 'amazing', 'perfect', 'wonderful', 'great']
            negative_words = ['expensive', 'costly', 'difficult', 'impossible', 'sorry']
            
            positive_count = sum(1 for word in positive_words if word in email_content)
            negative_count = sum(1 for word in negative_words if word in email_content)
            
            if positive_count > negative_count:
                self.state_manager.update_interest_level(current_interest + 0.1)
            elif negative_count > positive_count:
                self.state_manager.update_interest_level(current_interest - 0.1)
            
        except Exception as e:
            logger.error(f"❌ Error analyzing email: {str(e)}")
    
    async def generate_and_send_response(self, wandero_email: Dict):
        """Generate response based on persona and send it"""
        try:
            # Calculate response delay based on mode
            delay_minutes = self.calculate_response_delay()
            
            if self.test_mode:
                logger.info(f"[TEST] Responding immediately (test mode)")
            else:
                logger.info(f"[DEMO] Waiting {delay_minutes:.1f} minutes before responding (persona behavior: {self.persona_data.get('personality', 'standard')})")
            
            # Wait for calculated delay
            await asyncio.sleep(delay_minutes * 60)
            
            # Generate response
            subject, body = await self.generate_response(wandero_email)
            
            # Send response
            result = self.gmail_client.send_email(
                to=self.wandero_email,
                subject=subject,
                body=body,
                thread_id=wandero_email['thread_id']
            )
            
            if result['success']:
                # Add to conversation history
                message = {
                    'id': result['message_id'],
                    'thread_id': result['thread_id'],
                    'subject': subject,
                    'body': body,
                    'sender': self.client_name,
                    'timestamp': result['timestamp']
                }
                
                self.state_manager.add_message(message)
                
                # Random chance to send a "forgot to mention" follow-up (only in demo mode)
                if not self.test_mode and random.random() < 0.15:  # 15% chance
                    await self.maybe_send_forgotten_detail(result['thread_id'])
                
                logger.info("[SUCCESS] Response sent successfully!")
                
            else:
                logger.error(f"[ERROR] Failed to send response: {result['error']}")
                
        except Exception as e:
            logger.error(f"[ERROR] Error generating/sending response: {str(e)}")
    
    def calculate_response_delay(self) -> float:
        """Calculate response delay in minutes based on persona"""
        # TEST MODE: Immediate response
        if self.test_mode:
            return 0.1  # Just 6 seconds for processing
        
        # DEMO MODE: Realistic timing (existing logic)
        state = self.state_manager.get_state()
        base_minutes = 60  # Base 1 hour
        
        # Personality factors
        personality = self.persona_data.get('personality', 'standard')
        if personality == 'spontaneous':
            base_minutes *= 0.3  # 20 minutes
        elif personality == 'cautious':
            base_minutes *= 2.0   # 2 hours
        elif personality == 'budget-conscious':
            base_minutes *= 1.5   # 1.5 hours
        elif personality == 'independent':
            base_minutes *= 0.8   # 48 minutes
        
        # Interest level factors
        interest = state.get('interest_level', 0.5)
        if interest > 0.7:
            base_minutes *= 0.5  # Respond faster when very interested
        elif interest < 0.3:
            base_minutes *= 2.0  # Respond slower when not interested
        
        # Time of day factors (simplified)
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:  # Business hours
            base_minutes *= 0.7
        elif current_hour >= 22 or current_hour <= 6:  # Late night/early morning
            base_minutes *= 3.0
        
        # Add randomness (±30%)
        variance = base_minutes * 0.3
        actual_minutes = base_minutes + random.uniform(-variance, variance)
        
        # Minimum 1 minute, maximum 8 hours for demo
        return max(1, min(480, actual_minutes))
    
    async def generate_initial_inquiry(self) -> tuple[str, str]:
        """Generate initial inquiry email"""
        prompt = f"""
        You are {self.persona_data['name']} writing your FIRST email to a travel agency.
        
        Company Information:
        - Name: {self.company_info.get('name', 'Travel Agency')}
        - Country: {self.company_info.get('country', 'Unknown')}
        - Specialties: {', '.join(self.company_info.get('specialties', []))}
        
        Your profile:
        - Personality: {self.persona_data.get('personality', 'standard')}
        - Travel Group: {self.persona_data.get('travel_group', 'solo')}
        - Interests: {', '.join(self.persona_data.get('interests', []))}
        - Decision Style: {self.persona_data.get('decision_style', 'standard')}
        
        Write a natural initial inquiry that:
        1. Shows interest in {self.company_info.get('country', 'travel')}
        2. Shares 1-2 key details about yourself/group (but NOT everything - save budget, exact dates, special requirements for later)
        3. Asks a general question about their services
        4. Matches your personality exactly
        
        Personality guidelines:
        - Cautious: Formal, asks about safety, detailed
        - Spontaneous: Casual, enthusiastic, quick
        - Budget-conscious: Mentions cost concerns early
        - Independent: Professional, direct
        
        DO NOT share all details at once. Be realistic - people don't share everything in first email.
        
        Format your response as:
        SUBJECT: [subject line]
        BODY: [email body with proper greeting and sign-off]
        """
        
        response = self.llm.invoke(prompt)
        return self._parse_email_response(response.content)
    
    async def generate_response(self, wandero_email: Dict) -> tuple[str, str]:
        """Generate response to Wandero's email"""
        state = self.state_manager.get_state()
        
        prompt = f"""
        You are {self.persona_data['name']} responding to a travel agency email.
        
        Your personality: {self.persona_data.get('personality', 'standard')}
        Current conversation phase: {state['phase']}
        Your interest level: {state['interest_level']}/1.0
        
        Wandero's email:
        Subject: {wandero_email['subject']}
        Body: {wandero_email['body']}
        
        Your background (don't share everything at once):
        - Budget: ${self.persona_data.get('budget', {}).get('min', 1000)}-${self.persona_data.get('budget', {}).get('max', 2000)}
        - Travel dates: {self.persona_data.get('travel_dates', 'flexible')}
        - Group: {self.persona_data.get('travel_group', 'solo')}
        - Interests: {', '.join(self.persona_data.get('interests', []))}
        - Concerns: {', '.join(self.persona_data.get('worries', []))}
        - Special needs: {', '.join(self.persona_data.get('special_requirements', []))}
        
        Information you've already shared:
        {self._get_shared_info_summary(state)}
        
        Response guidelines based on conversation phase:
        
        If INFORMATION_GATHERING phase:
        - Answer their questions naturally
        - Share requested information but not everything at once
        - Ask follow-up questions
        - Show your personality traits
        
        If PROPOSAL_REVIEW phase:
        - React according to your personality and budget
        - Ask questions about concerns from your worry list
        - Show interest or concern appropriately
        
        If NEGOTIATION phase:
        - Negotiate based on your flexibility
        - Budget-conscious: Push for discounts
        - Cautious: Ask more safety questions
        - Spontaneous: Show excitement but ask about experiences
        
        Behavioral rules:
        1. Stay true to your personality throughout
        2. Don't share information they didn't ask for
        3. Show realistic human behavior (sometimes misunderstand, ask for clarification)
        4. Reference previous messages naturally
        5. Make it feel like a real person wrote this
        
        Format your response as:
        SUBJECT: [subject line - usually "Re: [their subject]"]
        BODY: [natural email response]
        """
        
        response = self.llm.invoke(prompt)
        return self._parse_email_response(response.content)
    
    def _get_shared_info_summary(self, state: Dict) -> str:
        """Get summary of what information has been shared"""
        shared = state.get('shared_info', {})
        summary = []
        
        if shared.get('budget'):
            summary.append("Budget range")
        if shared.get('dates'):
            summary.append("Travel dates")
        if shared.get('group_size'):
            summary.append("Group composition")
        if shared.get('interests'):
            summary.append("Travel interests")
        if shared.get('special_requirements'):
            summary.append("Special requirements")
            
        return ', '.join(summary) if summary else "Nothing specific yet"
    
    async def maybe_send_forgotten_detail(self, thread_id: str):
        """Maybe send a follow-up email with forgotten detail"""
        state = self.state_manager.get_state()
        forgot_to_mention = state.get('forgot_to_mention', [])
        
        if not forgot_to_mention:
            return
            
        # Wait a bit (2-10 minutes)
        delay_minutes = random.uniform(2, 10)
        logger.info(f"💭 Will send 'forgot to mention' follow-up in {delay_minutes:.1f} minutes...")
        await asyncio.sleep(delay_minutes * 60)
        
        forgotten_item = random.choice(forgot_to_mention)
        
        prompt = f"""
        You are {self.persona_data['name']} and you just realized you forgot to mention something important in your previous email.
        
        You forgot to mention: {forgotten_item}
        
        Write a brief, natural follow-up email mentioning this.
        Don't over-apologize - just mention it casually like a real person would.
        
        Format:
        SUBJECT: [subject - something like "Re: [previous] - One more thing"]
        BODY: [brief follow-up email]
        """
        
        response = self.llm.invoke(prompt)
        subject, body = self._parse_email_response(response.content)
        
        # Send follow-up email
        result = self.gmail_client.send_email(
            to=self.wandero_email,
            subject=subject,
            body=body,
            thread_id=thread_id
        )
        
        if result['success']:
            # Remove from forgot list
            state['forgot_to_mention'].remove(forgotten_item)
            
            # Add to conversation
            message = {
                'id': result['message_id'],
                'thread_id': result['thread_id'],
                'subject': subject,
                'body': body,
                'sender': self.client_name,
                'timestamp': result['timestamp']
            }
            
            self.state_manager.add_message(message)
            logger.info(f"💭 Sent forgotten detail follow-up: {forgotten_item}")
    
    def _parse_email_response(self, response: str) -> tuple[str, str]:
        """Parse LLM response into subject and body"""
        lines = response.strip().split('\n')
        subject = "Travel Inquiry"
        body_lines = []
        
        in_body = False
        for line in lines:
            if line.upper().startswith("SUBJECT:"):
                subject = line.split(":", 1)[1].strip()
            elif line.upper().startswith("BODY:"):
                in_body = True
            elif in_body or (subject != "Travel Inquiry" and not line.upper().startswith("SUBJECT:")):
                body_lines.append(line)
        
        body = '\n'.join(body_lines).strip()
        
        # Clean up common formatting issues
        if body.startswith('BODY:'):
            body = body[5:].strip()
            
        return subject, body