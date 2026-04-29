from __future__ import annotations

import os
import sys

from dotenv import load_dotenv


def check_prerequisites() -> bool:
    from .display import print_error

    # Check Ollama is running
    try:
        import ollama
        ollama.list()
    except Exception:
        print_error(
            "Cannot connect to Ollama. Make sure it's running:\n"
            "  brew services start ollama\n"
            "  # or: ollama serve"
        )
        return False

    # Check the model is available
    try:
        import ollama
        models = ollama.list()
        model_names = [m.model for m in models.models]
        if not any("gemma4" in name for name in model_names):
            print_error(
                "gemma4 model not found. Pull it with:\n"
                "  ollama pull gemma4:31b"
            )
            return False
    except Exception as e:
        print_error(f"Error checking models: {e}")
        return False

    # Check SerpApi key
    if not os.environ.get("SERPAPI_API_KEY"):
        print_error(
            "SERPAPI_API_KEY not set. Get a free key at https://serpapi.com\n"
            "Then add it to your .env file:\n"
            "  echo 'SERPAPI_API_KEY=your_key' > .env"
        )
        return False

    return True


def main() -> None:
    load_dotenv()

    from .agent import BookingAgent
    from .display import (
        get_user_input,
        print_assistant,
        print_error,
        print_welcome,
        thinking_spinner,
    )

    if not check_prerequisites():
        sys.exit(1)

    print_welcome()
    agent = BookingAgent()

    while True:
        user_input = get_user_input()

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print_assistant("Goodbye! Happy travels!")
            break

        try:
            with thinking_spinner():
                response = agent.chat(user_input)
            print_assistant(response)
        except KeyboardInterrupt:
            print_assistant("\nGoodbye!")
            break
        except Exception as e:
            print_error(f"Something went wrong: {e}")


if __name__ == "__main__":
    main()
