"""chat.py

This module provides the ChatService class, which facilitates AI-driven
chat.

Key Features:
- Processes user queries and generates responses using the AIModel.
- Handles special cases like GUI prompts and formats output for better
  readability.
- Supports integration with LangChain messages and tools.

"""

import re
from typing import Any, Dict, Final, List

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from backend.ai_graph import AIGraph
from backend.config import settings

PROMPT_TOOL: Final[str] = "[GUI_PROMPT_NEEDED]"
BULLET_PATTERN: Final[str] = r"(^|\<br\>)(\*|\-|\•)\s"


class ChatService:
    """Service class for handling chat interactions with AI agents."""

    def __init__(self, mcp_service=None):
        """Initialize the chat service with an AI model.

        Args:
            mcp_service: MCP service for command execution (optional)
        """
        self.agent_graph = AIGraph(
            debug=settings.debug,
            provider=settings.llm_provider,
            api_base=settings.llm_api_base,
            api_key=settings.llm_api_key,
            model_name=settings.llm_model,
            mcp_service=mcp_service,
            auto_execute=settings.auto_execute_commands,
            default_container=settings.default_executor_container,
        )

    def _format_ai_message(self, message: AIMessage) -> Dict[str, Any]:
        """Format an AI message for response."""
        response_text = None

        match message.content:
            case str() as content if PROMPT_TOOL in content:
                prompt_text = content.split(PROMPT_TOOL)[1]
                response_text = f"I need more information: {prompt_text}"
            case list([dict() as content]):
                response_text = str(content.get("text"))
            case _:
                response_text = str(message.content)

        response = {}

        if "reasoning_content" in message.additional_kwargs:
            kwargs = message.additional_kwargs
            reasoning_text = str(kwargs.get("reasoning_content"))
            response |= {"reasoning": reasoning_text}

        if response_text:
            formatted_text = re.sub(BULLET_PATTERN, r"\1• ", response_text)
            response |= {"response": formatted_text}

        return response

    def chat(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """Process a chat history and return the AI response."""
        response = []

        try:
            for event in self.agent_graph.chat(messages):
                agent = event[1]
                _, y = next(iter(agent.items()))
                _, messages = next(iter(y.items()))
                if not messages:
                    continue
                message: BaseMessage = messages[0]

                name = message.name

                match message:
                    case AIMessage():
                        formatted_message = self._format_ai_message(message)
                        response.append({"name": name, **formatted_message})
                    case ToolMessage(content=text) if PROMPT_TOOL in text:
                        prompt_text = text.split(PROMPT_TOOL)[1]
                        resp_text = f"I need more information: {prompt_text}"
                        response.append({"name": name, "response": resp_text})

        except Exception as e:
            print(f"Error in chat processing: {e}")
            return {
                "name": "System",
                "response": "Error processing chat request.",
            }

        if not response:
            return {
                "name": "System",
                "response": "No response generated.",
            }

        return response[-1]

    def get_graph(self) -> bytes:
        """Return the AI model's graph visualization as PNG bytes."""
        return self.agent_graph.get_graph()
