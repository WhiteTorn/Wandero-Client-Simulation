"""Build the client conversation graph"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from client_state import ClientState
from client_nodes import (
    initial_inquiry_node,
    analyze_wandero_response_node,
    provide_details_node,
    send_correction_node,
    review_proposal_node,
    end_conversation_node
)
from client_router import conversation_router
from personas import PERSONAS

def create_client_graph(persona_type: str = "worried_parent"):
    """Create the client conversation graph with proper state management"""
    
    print("🏗️ Building LangGraph workflow...")
    
    # Create the graph
    workflow = StateGraph(ClientState)
    
    # Add all nodes
    workflow.add_node("initial_inquiry", initial_inquiry_node)
    workflow.add_node("analyze_response", analyze_wandero_response_node)
    workflow.add_node("provide_details", provide_details_node)
    workflow.add_node("send_correction", send_correction_node)
    workflow.add_node("review_proposal", review_proposal_node)
    workflow.add_node("end_conversation", end_conversation_node)
    
    # Set the entry point
    workflow.set_entry_point("initial_inquiry")
    
    # Add conditional edges from a central routing point
    workflow.add_conditional_edges(
        "initial_inquiry",
        lambda x: "analyze_response"  # Always go to analyze after initial
    )
    
    workflow.add_conditional_edges(
        "analyze_response",
        conversation_router,
        {
            "provide_details": "provide_details",
            "review_proposal": "review_proposal", 
            "send_correction": "send_correction",
            "end_conversation": "end_conversation",
            "analyze_response": "analyze_response"
        }
    )
    
    workflow.add_conditional_edges(
        "provide_details",
        lambda x: "send_correction" if x.get("needs_correction") else "analyze_response"
    )
    
    workflow.add_edge("send_correction", "analyze_response")
    workflow.add_edge("review_proposal", "end_conversation")
    workflow.add_edge("end_conversation", END)
    
    # Compile with memory
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    print("✅ Graph compiled successfully!")
    return app

def create_initial_state(persona_type: str) -> ClientState:
    """Create the initial state for a persona"""
    persona = PERSONAS[persona_type]
    
    return {
        "messages": [],
        "phase": "initial_inquiry",
        "provided_info": {
            "inquiry_sent": False,
            "travelers_count": False,
            "dates": False,
            "ages": False,
            "budget": False,
            "special_needs": False
        },
        "persona_name": persona["name"],
        "persona_type": persona["type"],
        "wandero_requests": [],
        "turn_count": 0,
        "needs_correction": False,
        "forgotten_details": []
    }