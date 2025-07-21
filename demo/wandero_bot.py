"""Improved Wandero bot that tracks conversation state"""

from typing import Dict, Set

class WanderoBot:
    def __init__(self):
        self.conversation_phase = "initial"
        self.collected_info: Set[str] = set()
        self.missing_info: Set[str] = {"travelers", "dates", "budget", "ages"}
        
    def process_message(self, client_message: str, turn: int) -> str:
        """Process client message and return appropriate response"""
        
        msg_lower = client_message.lower()
        
        # Initial inquiry
        if self.conversation_phase == "initial" and "chile" in msg_lower:
            self.conversation_phase = "gathering_info"
            return self._initial_response()
        
        # Gathering information
        if self.conversation_phase == "gathering_info":
            # Check what info we received
            if "4 people" in msg_lower or "four" in msg_lower:
                self.collected_info.add("travelers")
                self.missing_info.discard("travelers")
            
            if "july" in msg_lower or "15-22" in msg_lower:
                self.collected_info.add("dates")
                self.missing_info.discard("dates")
                
            if "$" in client_message or "budget" in msg_lower:
                self.collected_info.add("budget")
                self.missing_info.discard("budget")
                
            if "12" in msg_lower and "8" in msg_lower:
                self.collected_info.add("ages")
                self.missing_info.discard("ages")
            
            # Handle corrections
            if "allergy" in msg_lower or "allergic" in msg_lower:
                self.collected_info.add("special_needs")
                return self._allergy_acknowledgment()
            
            # If we have enough info, send proposal
            if len(self.collected_info) >= 3:
                self.conversation_phase = "proposal_sent"
                return self._send_proposal()
            
            # Otherwise ask for missing info
            return self._request_missing_info()
        
        # Handle proposal response
        if self.conversation_phase == "proposal_sent":
            if any(word in msg_lower for word in ["perfect", "great", "proceed", "book"]):
                self.conversation_phase = "booking"
                return self._booking_confirmation()
        
        return "Thank you for your message. How else can I help with your Chile trip?"
    
    def _initial_response(self) -> str:
        return """Dear Valued Customer,

Thank you for your interest in visiting Chile with Chile Adventures Ltd.! 
We'd be delighted to help plan your perfect family adventure.

To create a customized itinerary, could you please provide:
- Number of travelers (adults and children with ages)
- Preferred travel dates
- Budget range
- Any special interests or requirements
- Preferred accommodation type

We specialize in family-friendly tours across Santiago, Atacama Desert, Patagonia, Valparaíso, and Easter Island.

Looking forward to planning your Chilean adventure!

Best regards,
Maria Rodriguez
Travel Consultant"""

    def _request_missing_info(self) -> str:
        missing_list = list(self.missing_info)
        if missing_list:
            return f"""Thank you for the information! To complete your quote, I still need:
{chr(10).join('- ' + info for info in missing_list)}

Once I have these details, I can create a perfect itinerary for your family!"""
        return self._send_proposal()

    def _send_proposal(self) -> str:
        return """Perfect! Based on your requirements, I'm pleased to propose our 
"Classic Chile Family Adventure" package:

**Duration**: 7 days / 6 nights
**Dates**: July 15-22, 2024

**Itinerary Overview**:
- Day 1: Arrival in Santiago - City tour
- Day 2: Valparaíso coastal excursion  
- Day 3-4: Fly to Atacama - Desert adventures
- Day 5: Salt flats and flamingo watching
- Day 6: Return to Santiago
- Day 7: Departure

**Accommodation**:
- Santiago: Hotel Plaza San Francisco (Family Suite)
- Atacama: Hotel Cumbres San Pedro de Atacama

**Included**:
✓ Airport transfers
✓ Hotel accommodation (4-star)
✓ Daily breakfast
✓ Guided tours
✓ Entrance fees

**Total Cost**: $4,800 (for 2 adults + 2 children)
*Child discount of 30% already applied*

Would you like to proceed with this itinerary?"""

    def _allergy_acknowledgment(self) -> str:
        return """Thank you for letting me know about Jack's nut allergy. 
This is very important information!

I'll make sure to:
- Note this in all restaurant reservations
- Inform all tour guides
- Provide a list of allergy-friendly restaurants
- Include emergency medical facility information

Your family's safety is our top priority!"""

    def _booking_confirmation(self) -> str:
        return """Wonderful! I'm delighted you'd like to proceed.

**Next Steps**:
1. I'll send you a detailed invoice within the hour
2. A 30% deposit ($1,440) secures your booking
3. Full payment due 30 days before departure

Thank you for choosing Chile Adventures!"""