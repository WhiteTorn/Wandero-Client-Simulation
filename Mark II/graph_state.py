from typing import TypedDict, List, Dict, Literal, Optional
from datetime import datetime

class EmailMessage(TypedDict):
    """Email message structure"""
    subject: str
    body: str
    sender: str
    timestamp: datetime
    sentiment: Optional[float]  # -1 to 1
    
class ConversationState(TypedDict):
    """Shared state between both agents"""
    # Message history - removed add_messages annotation for custom email format
    messages: List[EmailMessage]
    
    # Client information (persistent memory)
    client_name: str
    client_email: str
    client_personality: str
    client_budget: Optional[Dict[str, int]]
    client_travel_dates: Optional[str]
    client_group_size: Optional[str]
    client_interests: List[str]
    client_concerns: List[str]
    client_special_requirements: List[str]
    
    # Company information
    company_name: str
    company_type: str
    agent_name: str
    
    # Conversation tracking
    phase: Literal["introduction", "discovery", "proposal", "negotiation", "closing", "abandoned"]
    interest_level: float  # 0-1
    abandonment_risk: float  # 0-1
    
    # Business tracking
    proposals_made: List[Dict]
    current_offer: Optional[Dict]
    discounts_offered: float
    
    # Time simulation
    current_time: datetime
    last_client_response_time: Optional[datetime]
    last_wandero_response_time: Optional[datetime]
    
    # Decision flags
    all_info_gathered: bool
    ready_to_book: bool
    conversation_ended: bool