from typing import Annotated, TypedDict, List, Dict, Literal
import operator

class ClientState(TypedDict):
    """Everything Our Client Remembers"""

    messages: Annotated[List[Dict[str, str]], operator.add]

    phase: Literal[
        "initial_inquiry",
        "providing_details",
        "reviering_proposal",
        "confirming"
    ]

    provided_info: Dict[str, bool]

    persona_name: str
    persona_traits: List[str]

    forgetten_details: List[str]