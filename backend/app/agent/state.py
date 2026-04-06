from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    rfp_text: str
    extracted: Optional[Dict[str, Any]]
    retrieved_products: Optional[List[Dict[str, Any]]]
    plan: Optional[Dict[str, Any]]
    generated_blocks: Optional[List[Dict[str, Any]]]
    proposal_uuid: Optional[str]
    evaluation: Optional[Dict[str, Any]]
    error: Optional[str]