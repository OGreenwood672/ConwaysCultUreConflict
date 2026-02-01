"""LLM client - AWS Bedrock wrapper for Claude models."""

import json
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class ModelTier(Enum):
    """Model tiers for different use cases."""
    FAST = "fast"      # Haiku - for quick decisions
    BALANCED = "balanced"  # Sonnet - for reflections and culture updates
    POWERFUL = "powerful"  # Opus - for complex reasoning (rarely needed)


@dataclass
class LLMConfig:
    """Configuration for LLM client."""
    aws_region: str = "us-east-1"
    # Use cross-region inference profile format for newer models
    fast_model_id: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    balanced_model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    powerful_model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    max_retries: int = 3
    default_max_tokens: int = 1024
    default_temperature: float = 0.7


class LLMClient:
    """
    AWS Bedrock client for Claude models.

    Provides different model tiers:
    - Fast (Haiku): Quick decisions, simple responses
    - Balanced (Sonnet): Reflections, culture updates
    - Powerful (Opus): Complex reasoning when needed
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._client = None

    def _get_client(self):
        """Lazy initialization of Bedrock client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "bedrock-runtime",
                    region_name=self.config.aws_region
                )
            except ImportError:
                raise RuntimeError("boto3 is required for AWS Bedrock. Install with: pip install boto3")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Bedrock client: {e}")
        return self._client

    def _get_model_id(self, tier: ModelTier) -> str:
        """Get the model ID for a given tier."""
        if tier == ModelTier.FAST:
            return self.config.fast_model_id
        elif tier == ModelTier.BALANCED:
            return self.config.balanced_model_id
        else:
            return self.config.powerful_model_id

    async def generate(self, prompt: str,
                      system_prompt: Optional[str] = None,
                      tier: ModelTier = ModelTier.FAST,
                      max_tokens: Optional[int] = None,
                      temperature: Optional[float] = None) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for context
            tier: Which model tier to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)

        Returns:
            Generated text response
        """
        client = self._get_client()
        model_id = self._get_model_id(tier)

        messages = [{"role": "user", "content": prompt}]

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or self.config.default_max_tokens,
            "temperature": temperature if temperature is not None else self.config.default_temperature,
            "messages": messages,
        }

        if system_prompt:
            body["system"] = system_prompt

        try:
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            response_body = json.loads(response["body"].read())
            return response_body["content"][0]["text"]

        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {e}")

    async def generate_with_retry(self, prompt: str,
                                  system_prompt: Optional[str] = None,
                                  tier: ModelTier = ModelTier.FAST,
                                  max_tokens: Optional[int] = None,
                                  temperature: Optional[float] = None) -> str:
        """Generate with automatic retry on failure."""
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                return await self.generate(
                    prompt, system_prompt, tier, max_tokens, temperature
                )
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        raise RuntimeError(f"LLM generation failed after {self.config.max_retries} attempts: {last_error}")

    async def generate_decision(self, context: str, perception: str,
                               available_actions: list[str]) -> dict:
        """
        Generate an action decision for an agent.

        Args:
            context: Full context (life + culture + soul + memories)
            perception: Current sensory input
            available_actions: List of possible actions

        Returns:
            Dict with 'action', 'target', and 'reasoning' keys
        """
        actions_str = "\n".join(f"- {a}" for a in available_actions)

        prompt = f"""{context}

## Current Perception
{perception}

## Available Actions
{actions_str}

## Decision Guidelines
- If people are nearby, consider communicating to build relationships or gather information
- If you need safety, build a shelter
- Move toward allies or away from threats
- Act according to your personality and goals

What do you do? Pick ONE action from the list above.

Respond in this exact JSON format:
{{
  "action": "<exact action with parameters, e.g. move(1, 0) or build(shelter) or communicate(2, 1)>",
  "target": "<target of action if applicable, or null>",
  "reasoning": "<brief internal thought process>",
  "speech": "<what you say out loud, or null if silent>"
}}

Response:"""

        response = await self.generate(
            prompt,
            system_prompt="You are an AI agent in a simulation. Respond only with valid JSON.",
            tier=ModelTier.FAST,
            max_tokens=300,
            temperature=0.8
        )

        try:
            # Try to parse JSON from response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "action": available_actions[0] if available_actions else "wait",
                "target": None,
                "reasoning": "Failed to parse decision",
                "speech": None
            }

    async def generate_chat_response(self, context: str,
                                    incoming_message: str,
                                    sender: str) -> str:
        """
        Generate a chat response to another agent.

        Args:
            context: Agent's context
            incoming_message: What the other agent said
            sender: Who said it

        Returns:
            Response message
        """
        prompt = f"""{context}

{sender} says to you: "{incoming_message}"

How do you respond? Stay in character based on your personality and relationship with {sender}.
Keep your response brief (1-2 sentences).

Your response:"""

        response = await self.generate(
            prompt,
            tier=ModelTier.FAST,
            max_tokens=150,
            temperature=0.9
        )

        return response.strip().strip('"')

    async def estimate_importance(self, event_description: str) -> float:
        """
        Estimate the importance of an event (1-10 scale).

        Uses the LLM to judge how significant an event is.
        """
        prompt = f"""On a scale of 1-10, how important is this event for an agent trying to survive and thrive?

Event: {event_description}

1 = Trivial (seeing a common block)
5 = Moderate (finding food, meeting someone)
10 = Critical (life-threatening danger, major discovery)

Respond with just a number from 1-10.

Importance:"""

        response = await self.generate(
            prompt,
            tier=ModelTier.FAST,
            max_tokens=10,
            temperature=0.3
        )

        try:
            # Extract number from response
            import re
            match = re.search(r'\d+', response)
            if match:
                importance = int(match.group())
                return float(max(1, min(10, importance)))
        except:
            pass

        return 5.0  # Default to moderate importance


class MockLLMClient:
    """Mock LLM client for testing without AWS credentials."""

    async def generate(self, prompt: str, **kwargs) -> str:
        """Return a simple mock response."""
        if "importance" in prompt.lower():
            return "5"
        if "json" in prompt.lower():
            return '{"action": "wait", "target": null, "reasoning": "mock response", "speech": null}'
        return "This is a mock response for testing."

    async def generate_with_retry(self, prompt: str, **kwargs) -> str:
        return await self.generate(prompt, **kwargs)

    async def generate_decision(self, context: str, perception: str,
                               available_actions: list[str]) -> dict:
        return {
            "action": available_actions[0] if available_actions else "wait",
            "target": None,
            "reasoning": "Mock decision",
            "speech": None
        }

    async def generate_chat_response(self, context: str,
                                    incoming_message: str,
                                    sender: str) -> str:
        return f"Hello, {sender}."

    async def estimate_importance(self, event_description: str) -> float:
        return 5.0
