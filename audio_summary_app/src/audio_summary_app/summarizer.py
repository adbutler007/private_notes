"""
Map-Reduce Summarizer
Implements a map-reduce approach to summarizing long transcripts:
1. MAP: Summarize individual chunks
2. REDUCE: Combine chunk summaries into a final summary
Uses Ollama for all summarization (on-device LLM)
"""

from typing import List, Dict, Optional
import threading
from datetime import datetime
import json
import ollama
from pydantic import BaseModel, Field

try:
    from .ollama_manager import ensure_model_ready
except ImportError:
    # Fallback for when imported without package context
    from ollama_manager import ensure_model_ready


# Pydantic models for structured data extraction
class ContactData(BaseModel):
    """Contact information from the meeting"""
    name: Optional[str] = Field(None, description="Full name of the contact")
    role: Optional[str] = Field(None, description="Job title or role")
    location: Optional[str] = Field(None, description="Geographic location")
    is_decision_maker: Optional[bool] = Field(None, description="Whether they are a decision maker")
    tenure_duration: Optional[str] = Field(None, description="Duration in current position if mentioned")


class CompanyData(BaseModel):
    """Company information from the meeting"""
    name: Optional[str] = Field(None, description="Company name")
    aum: Optional[str] = Field(None, description="Assets Under Management")
    icp_classification: Optional[int] = Field(None, description="ICP classification: 1 or 2")
    location: Optional[str] = Field(None, description="Geographic location")
    is_client: Optional[bool] = Field(None, description="Whether they are currently a client")
    competitor_products: Optional[List[str]] = Field(None, description="List of competitor products they hold")
    strategies_of_interest: Optional[List[str]] = Field(
        None,
        description="Strategies of interest: trend, carry, m.arb (market arbitrage), gold, btc"
    )


class DealData(BaseModel):
    """Deal information from the meeting"""
    ticket_size: Optional[str] = Field(None, description="Possible investment ticket size")
    products_of_interest: Optional[List[str]] = Field(
        None,
        description="Products of interest from: RSSB, RSST, RSBT, RSSY, RSBY, RSSX, RSBA, BTGD"
    )


class MeetingData(BaseModel):
    """Complete structured data extracted from meeting"""
    contacts: List[ContactData] = Field(default_factory=list, description="List of contacts discussed")
    companies: List[CompanyData] = Field(default_factory=list, description="List of companies discussed")
    deals: List[DealData] = Field(default_factory=list, description="List of deals or opportunities discussed")


class MapReduceSummarizer:
    """
    Map-Reduce style summarization of streaming transcripts
    - Map phase: Summarize individual time-based chunks
    - Reduce phase: Combine chunk summaries into coherent final summary
    """
    
    def __init__(
        self,
        model_name: str = "qwen3:4b-instruct",
        summary_interval: int = 300,
        chunk_summary_max_tokens: int = 200,
        final_summary_max_tokens: int = 500,
        chunk_summary_prompt: str = None,
        final_summary_prompt: str = None
    ):
        """
        Args:
            model_name: Ollama model name (default: qwen3:4b-instruct)
            summary_interval: Seconds between intermediate summaries
            chunk_summary_max_tokens: Max tokens for chunk summaries
            final_summary_max_tokens: Max tokens for final summary
            chunk_summary_prompt: Custom prompt for chunk summaries (uses default if None)
            final_summary_prompt: Custom prompt for final summary (uses default if None)
        """
        self.model_name = model_name
        self.summary_interval = summary_interval
        self.chunk_summary_max_tokens = chunk_summary_max_tokens
        self.final_summary_max_tokens = final_summary_max_tokens

        # Set prompts (use defaults if not provided)
        self.chunk_summary_prompt = chunk_summary_prompt or """Summarize the following conversation transcript concisely.
Focus on key points, topics discussed, and any important decisions or information.

Transcript:
{text}

Summary:"""

        self.final_summary_prompt = final_summary_prompt or """You are summarizing a conversation that was captured over time.
Below are summaries of different segments of the conversation.

Create a comprehensive final summary that:
1. Identifies the main topics and themes discussed
2. Highlights key points, decisions, or action items
3. Notes any important information or insights
4. Maintains chronological flow where relevant

Segment Summaries:
{summaries_text}

Final Comprehensive Summary:"""

        # Store intermediate summaries (in memory only)
        self.intermediate_summaries = []
        self.lock = threading.Lock()

        # Initialize the LLM
        self.llm = self._initialize_llm()
        
    def _initialize_llm(self):
        """
        Initialize the local LLM model using Ollama
        Automatically starts Ollama service and pulls model if needed
        """
        print(f"[LLM] Using Ollama model: {self.model_name}")
        print("[LLM] Using on-device inference (no data sent to cloud)")

        try:
            # Ensure Ollama is running and model is available
            if ensure_model_ready(self.model_name, auto_pull=True):
                return OllamaLLM(self.model_name)
            else:
                raise Exception("Failed to ensure model is ready")

        except Exception as e:
            print(f"[LLM] Failed to initialize Ollama: {e}")
            print(f"[LLM] Falling back to mock model for testing")
            print(f"[LLM] To use Ollama, install it from: https://ollama.com/")
            return MockLLM()
        
    def summarize_chunk(self, text: str) -> str:
        """
        MAP phase: Summarize a single chunk of transcript

        Args:
            text: Transcript text to summarize

        Returns:
            Summary of the chunk
        """
        if not text.strip():
            return ""

        # Use configured prompt template
        prompt = self.chunk_summary_prompt.format(text=text)

        try:
            summary = self.llm.generate(prompt, max_tokens=self.chunk_summary_max_tokens)
            return summary.strip()
        except Exception as e:
            print(f"Error generating chunk summary: {e}")
            return f"[Error summarizing chunk: {str(e)}]"
            
    def add_intermediate_summary(self, summary: str):
        """Store an intermediate summary for later reduction"""
        with self.lock:
            self.intermediate_summaries.append({
                'summary': summary,
                'timestamp': datetime.now()
            })
            
    def generate_final_summary(self, chunks: List[Dict] = None) -> str:
        """
        REDUCE phase: Generate final summary from intermediate summaries ONLY

        IMPORTANT: This method should ONLY use intermediate summaries (chunk summaries)
        created during the MAP phase. Raw transcripts should never reach this method.

        Args:
            chunks: DEPRECATED - Not used. Kept for backward compatibility but should be None.
                    Final summary is generated ONLY from intermediate_summaries.

        Returns:
            Final comprehensive summary
        """
        with self.lock:
            if not self.intermediate_summaries:
                return "No content to summarize. No intermediate summaries available."

            # ONLY use intermediate summaries - never use raw transcript chunks
            summaries_text = "\n\n".join(
                f"[{i+1}] {s['summary']}"
                for i, s in enumerate(self.intermediate_summaries)
            )

            print(f"[REDUCE] Combining {len(self.intermediate_summaries)} intermediate summaries...")
            print(f"[REDUCE] Raw transcripts are NOT used - only chunk summaries")
                
        # Generate final summary using configured prompt template
        final_prompt = self.final_summary_prompt.format(summaries_text=summaries_text)

        try:
            final_summary = self.llm.generate(final_prompt, max_tokens=self.final_summary_max_tokens)
            
            # Add metadata
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            full_summary = f"""Summary Generated: {timestamp}
Number of Segments: {len(self.intermediate_summaries) if self.intermediate_summaries else len(chunks)}

{final_summary.strip()}
"""
            
            return full_summary
            
        except Exception as e:
            print(f"Error generating final summary: {e}")
            return f"[Error generating final summary: {str(e)}]"
            
    def clear_intermediate_summaries(self):
        """Clear intermediate summaries from memory"""
        with self.lock:
            self.intermediate_summaries.clear()

    def extract_structured_data(self, data_extraction_prompt: str) -> Dict:
        """
        Extract structured data from intermediate summaries using Ollama structured outputs

        This is called AFTER final summary generation to extract contact, company, and deal data
        into a structured JSON format using the MeetingData schema.

        Args:
            data_extraction_prompt: Prompt template with {summaries_text} placeholder

        Returns:
            Dictionary containing structured meeting data (contacts, companies, deals)
        """
        with self.lock:
            if not self.intermediate_summaries:
                return {
                    "contacts": [],
                    "companies": [],
                    "deals": []
                }

            # Format all intermediate summaries
            summaries_text = "\n\n".join(
                f"[Segment {i+1}] {s['summary']}"
                for i, s in enumerate(self.intermediate_summaries)
            )

            print(f"[DATA EXTRACTION] Extracting structured data from {len(self.intermediate_summaries)} summaries...")

        # Generate the extraction prompt
        prompt = data_extraction_prompt.format(summaries_text=summaries_text)

        # Add the JSON schema to the prompt to ground the model's response
        schema = MeetingData.model_json_schema()
        schema_str = json.dumps(schema, indent=2)
        full_prompt = f"{prompt}\n\nJSON Schema:\n{schema_str}"

        try:
            # Use Ollama's structured output with the MeetingData schema
            response = ollama.generate(
                model=self.model_name,
                prompt=full_prompt,
                format=schema,  # Pass the schema for structured output
                options={
                    'temperature': 0.0,  # Deterministic for data extraction
                    'num_predict': 2000,  # Enough tokens for structured data
                }
            )

            # Parse the response
            if hasattr(response, 'response'):
                json_text = response.response
            elif isinstance(response, dict) and 'response' in response:
                json_text = response['response']
            else:
                json_text = str(response)

            # Validate against the Pydantic model
            meeting_data = MeetingData.model_validate_json(json_text)

            # Convert to dictionary for easier handling
            result = meeting_data.model_dump()

            print(f"[DATA EXTRACTION] Successfully extracted:")
            print(f"  - {len(result['contacts'])} contact(s)")
            print(f"  - {len(result['companies'])} company/companies")
            print(f"  - {len(result['deals'])} deal(s)")

            return result

        except Exception as e:
            print(f"[DATA EXTRACTION] Error extracting structured data: {e}")
            print(f"[DATA EXTRACTION] Falling back to empty structure")
            return {
                "contacts": [],
                "companies": [],
                "deals": []
            }


class OllamaLLM:
    """
    Ollama LLM wrapper for on-device inference
    """

    def __init__(self, model_name: str):
        self.model_name = model_name

    def generate(self, prompt: str, max_tokens: int = 200) -> str:
        """
        Generate text using Ollama
        """
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    'num_predict': max_tokens,
                    'temperature': 0.7,
                    'top_k': 20,
                    'top_p': 0.8,
                    'repeat_penalty': 1,
                    'stop': ['<|im_start|>', '<|im_end|>'],
                }
            )

            # Handle different response formats
            # Some models use 'response' attribute, others use 'thinking' for chain-of-thought
            result = ""

            # Try to get response from the response object
            if hasattr(response, 'response') and response.response:
                result = response.response
            elif hasattr(response, 'thinking') and response.thinking:
                # Model is using reasoning/thinking mode
                result = response.thinking
            elif isinstance(response, dict) and 'response' in response:
                result = response['response']
            elif isinstance(response, dict) and 'thinking' in response:
                result = response['thinking']
            else:
                result = str(response)

            return result.strip()

        except Exception as e:
            print(f"[LLM] Error generating with Ollama: {e}")
            return f"[Error: {str(e)}]"


class MockLLM:
    """
    Mock LLM for prototype demonstration or when Ollama is not available
    """

    def generate(self, prompt: str, max_tokens: int = 200) -> str:
        """
        Simulate LLM generation
        """
        import hashlib
        import time

        # Simulate processing time
        time.sleep(0.5)

        # Generate a mock summary based on prompt hash (for consistency)
        hash_val = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)

        templates = [
            "The conversation covered topics including project updates, technical discussions, and planning. Key points included progress on deliverables and upcoming milestones.",
            "Discussion focused on technical implementation details, design decisions, and resource allocation. Several action items were identified for follow-up.",
            "The session included brainstorming, problem-solving, and decision-making regarding project direction. Important insights were shared about current challenges.",
            "Topics ranged from strategic planning to operational details. Participants discussed priorities, timelines, and coordination across teams.",
            "The conversation addressed current issues, proposed solutions, and next steps. Agreement was reached on several key points moving forward."
        ]

        return templates[hash_val % len(templates)]
