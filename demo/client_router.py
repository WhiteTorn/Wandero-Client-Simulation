"""Router functions for conditional edges"""

from typing import Literal
from client_state import ClientState

def conversation_router(state: ClientState) -> Literal[
    "analyze_response", 
    "provide_details", 
    "send_correction", 
    "review_proposal",
    "end_conversation"
]:
    """Determine next node based on current state"""
    
    print(f"🧭 Router: Current phase = {state['phase']}, Turn = {state['turn_count']}")
    
    # End if too many turns
    if state["turn_count"] > 10:
        return "end_conversation"
    
    # Route based on phase
    if state["phase"] == "awaiting_wandero_response":
        return "analyze_response"
    
    elif state["phase"] == "providing_details":
        return "provide_details"
    
    elif state["phase"] == "reviewing_proposal":
        return "review_proposal"
    
    elif state["phase"] == "confirming_booking":
        return "end_conversation"
    
    # Check if we need to send correction
    if state.get("needs_correction", False) and state["turn_count"] < 8:
        return "send_correction"
    
    return "analyze_response"