"""Define the client conversation state"""

from typing import TypedDict, List, Dict, Literal, Annotated
from typing_extensions import TypedDict
import operator

class ClientState(TypedDict):
    """State for client conversation - this is the heart of LangGraph"""
    
    # Message history with all emails
    messages: Annotated[List[Dict[str, str]], operator.add]
    
    # Current conversation phase
    phase: Literal[
        "initial_inquiry",
        "awaiting_wandero_response", 
        "providing_details",
        "sending_correction",
        "reviewing_proposal",
        "confirming_booking",
        "conversation_ended"
    ]
    
    # What information we've already provided
    provided_info: Dict[str, bool]
    
    # Persona information
    persona_name: str
    persona_type: str
    
    # Wandero's last request
    wandero_requests: List[str]
    
    # Counter to prevent infinite loops
    turn_count: int
    
    # Flag for whether we need to send a correction
    needs_correction: bool
    
    # What we forgot to mention
    forgotten_details: List[str]