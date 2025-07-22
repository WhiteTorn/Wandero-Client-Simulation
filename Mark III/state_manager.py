import json
import os
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, persona_type: str, wandero_email: str):
        """
        Initialize state manager with JSON persistence
        
        Args:
            persona_type: Type of persona being simulated
            wandero_email: Email address of Wandero agent
        """
        self.persona_type = persona_type
        self.wandero_email = wandero_email
        
        # Create unique state file for this conversation
        safe_email = wandero_email.replace('@', '_at_').replace('.', '_')
        self.state_file = f"conversation_state_{persona_type}_{safe_email}.json"
        
        # Ensure states directory exists
        self.states_dir = Path("conversation_states")
        self.states_dir.mkdir(exist_ok=True)
        self.state_path = self.states_dir / self.state_file
        
        self.state = self._load_or_initialize_state()
        
    def _load_or_initialize_state(self) -> Dict:
        """Load existing state or create new one"""
        if self.state_path.exists():
            try:
                with open(self.state_path, 'r') as f:
                    state = json.load(f)
                    
                # Convert timestamp strings back to datetime objects
                self._deserialize_timestamps(state)
                
                logger.info(f"📁 Loaded existing conversation state from {self.state_file}")
                logger.info(f"   Phase: {state.get('phase', 'unknown')}")
                logger.info(f"   Messages: {len(state.get('messages', []))}")
                logger.info(f"   Interest Level: {state.get('interest_level', 0.5)}")
                
                return state
                
            except Exception as e:
                logger.error(f"❌ Error loading state file: {str(e)}")
                logger.info("Creating fresh state...")
                
        # Create new state
        return self._initialize_fresh_state()
    
    def _initialize_fresh_state(self) -> Dict:
        """Initialize a fresh conversation state"""
        from personas import PERSONAS
        
        persona_data = PERSONAS.get(self.persona_type)
        if not persona_data:
            raise ValueError(f"Unknown persona type: {self.persona_type}")
            
        state = {
            # Persona info
            "persona_type": self.persona_type,
            "persona_data": persona_data,
            "wandero_email": self.wandero_email,
            
            # Message history
            "messages": [],
            "last_processed_message_id": None,
            
            # Client information (starts empty, gets filled as conversation progresses)
            "client_name": persona_data["name"],
            "client_email": f"{persona_data['name'].lower().replace(' ', '.')}@email.com",
            "client_personality": persona_data.get("personality", "standard"),
            "client_budget": None,
            "client_travel_dates": None,
            "client_group_size": None,
            "client_interests": [],
            "client_concerns": persona_data.get("worries", []).copy(),
            "client_special_requirements": persona_data.get("special_requirements", []).copy(),
            
            # Company information
            "company_info": {},  # Will be set when first email received
            
            # Conversation tracking
            "phase": "initial",  # initial, information_gathering, proposal_review, negotiation, booking, completed
            "interest_level": 0.5,
            "abandonment_risk": 0.1,
            
            # Business tracking
            "proposals_received": [],
            "current_offer": None,
            "discounts_mentioned": 0.0,
            
            # Behavioral state
            "shared_info": {
                "budget": False,
                "dates": False,
                "group_size": False,
                "interests": False,
                "special_requirements": False
            },
            "pending_questions": [],
            "forgot_to_mention": persona_data.get("special_requirements", []).copy(),
            
            # Timing and tracking
            "conversation_start": datetime.now(),
            "last_client_response": None,
            "last_wandero_response": None,
            "wandero_response_times": [],  # Track how long Wandero takes to respond
            
            # Decision flags
            "ready_to_book": False,
            "conversation_ended": False
        }
        
        logger.info(f"🆕 Created fresh conversation state for {persona_data['name']}")
        logger.info(f"   Personality: {persona_data.get('personality', 'standard')}")
        logger.info(f"   Budget: ${persona_data.get('budget', {}).get('min', 'unknown')}-${persona_data.get('budget', {}).get('max', 'unknown')}")
        logger.info(f"   Interests: {', '.join(persona_data.get('interests', []))}")
        
        return state
    
    def save_state(self):
        """Save current state to JSON file"""
        try:
            # Create a copy for serialization
            state_to_save = self.state.copy()
            
            # Convert datetime objects to ISO strings
            self._serialize_timestamps(state_to_save)
            
            # Save to file
            with open(self.state_path, 'w') as f:
                json.dump(state_to_save, f, indent=2, default=str)
                
            logger.debug(f"💾 State saved to {self.state_file}")
            
        except Exception as e:
            logger.error(f"❌ Error saving state: {str(e)}")
    
    def _serialize_timestamps(self, state: Dict):
        """Convert datetime objects to ISO strings for JSON serialization"""
        timestamp_fields = [
            'conversation_start', 'last_client_response', 'last_wandero_response'
        ]
        
        for field in timestamp_fields:
            if field in state and isinstance(state[field], datetime):
                state[field] = state[field].isoformat()
                
        # Handle messages timestamps
        for msg in state.get('messages', []):
            if 'timestamp' in msg and isinstance(msg['timestamp'], datetime):
                msg['timestamp'] = msg['timestamp'].isoformat()
    
    def _deserialize_timestamps(self, state: Dict):
        """Convert ISO strings back to datetime objects"""
        timestamp_fields = [
            'conversation_start', 'last_client_response', 'last_wandero_response'
        ]
        
        for field in timestamp_fields:
            if field in state and isinstance(state[field], str):
                try:
                    state[field] = datetime.fromisoformat(state[field])
                except:
                    state[field] = None
                    
        # Handle messages timestamps
        for msg in state.get('messages', []):
            if 'timestamp' in msg and isinstance(msg['timestamp'], str):
                try:
                    msg['timestamp'] = datetime.fromisoformat(msg['timestamp'])
                except:
                    msg['timestamp'] = datetime.now()
    
    def add_message(self, message: Dict):
        """Add message to conversation history"""
        self.state['messages'].append(message)
        
        # Track sender timings
        if message['sender'] == self.state['client_name']:
            self.state['last_client_response'] = message['timestamp']
        else:
            self.state['last_wandero_response'] = message['timestamp']
            
        self.save_state()
        
        logger.info(f"💬 Message added to conversation")
        logger.info(f"   From: {message['sender']}")
        logger.info(f"   Subject: {message.get('subject', 'No subject')}")
    
    def update_phase(self, new_phase: str):
        """Update conversation phase"""
        old_phase = self.state.get('phase', 'unknown')
        self.state['phase'] = new_phase
        self.save_state()
        
        logger.info(f"🔄 Phase changed: {old_phase} → {new_phase}")
    
    def update_interest_level(self, new_level: float):
        """Update client interest level"""
        old_level = self.state.get('interest_level', 0.5)
        self.state['interest_level'] = max(0, min(1, new_level))
        self.save_state()
        
        if abs(new_level - old_level) > 0.1:  # Only log significant changes
            logger.info(f"📈 Interest level: {old_level:.2f} → {new_level:.2f}")
    
    def get_state(self) -> Dict:
        """Get current state"""
        return self.state.copy()
    
    def is_conversation_ended(self) -> bool:
        """Check if conversation has ended"""
        return self.state.get('conversation_ended', False)
    
    def get_last_processed_message_id(self) -> Optional[str]:
        """Get ID of last processed message to avoid duplicates"""
        return self.state.get('last_processed_message_id')
    
    def set_last_processed_message_id(self, message_id: str):
        """Set last processed message ID"""
        self.state['last_processed_message_id'] = message_id
        self.save_state()