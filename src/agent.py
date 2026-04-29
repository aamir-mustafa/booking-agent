from __future__ import annotations

import ollama

from .display import print_source, print_tool_call, print_tool_result
from .models import BookingState
from .prompts import build_system_prompt
from .tools import TOOL_DEFINITIONS, execute_tool

MODEL = "gemma4:31b"
NUM_CTX = 16384
MAX_HISTORY_MESSAGES = 40  # sliding window: keep last N messages (excluding system)
MAX_TOOL_ROUNDS = 5  # prevent infinite tool-call loops


class BookingAgent:
    def __init__(self) -> None:
        self.state = BookingState()
        self.messages: list[dict] = []

    def _build_messages(self) -> list[dict]:
        system_msg = {"role": "system", "content": build_system_prompt(self.state)}
        # Sliding window: keep only the most recent messages
        history = self.messages[-MAX_HISTORY_MESSAGES:]
        return [system_msg] + history

    def chat(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        used_tools = False
        for _ in range(MAX_TOOL_ROUNDS):
            response = ollama.chat(
                model=MODEL,
                messages=self._build_messages(),
                tools=TOOL_DEFINITIONS,
                options={"num_ctx": NUM_CTX, "temperature": 0.7},
            )

            msg = response.message

            # If no tool calls, we have a final text response
            if not msg.tool_calls:
                content = msg.content or ""
                self.messages.append({"role": "assistant", "content": content})
                if not used_tools:
                    print_source("Model's own knowledge (no API called)")
                return content

            used_tools = True

            # Process tool calls
            # Append the assistant message with tool calls to history
            self.messages.append(msg.model_dump())

            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = tool_call.function.arguments

                print_tool_call(fn_name, fn_args)
                result = execute_tool(fn_name, fn_args, self.state)
                print_tool_result(fn_name, result)

                self.messages.append({
                    "role": "tool",
                    "content": result,
                })

            # Loop back to let the model process the tool results

        # If we hit the max tool rounds, return whatever content we have
        return msg.content or "I encountered an issue processing your request. Could you try again?"
