import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from client_state import ClientState

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model = "gemini-1.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7 # Naturality
)

def initial_inquiry_node(state: ClientState) -> Dict