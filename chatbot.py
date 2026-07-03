#!/usr/bin/env python3
"""
Custom AI Chatbot with Memory
DecodeLabs — Generative AI Project 1

Implements:
  - Stateful chat session via an in-memory history list (role/content objects)
  - Structural Validation Gate: blocks empty/whitespace input before it reaches the API
  - Terminal Append Sequence: ingest+append user turn, transmit, record model turn
  - Sliding Window Algorithm: FIFO-prunes the oldest message pairs once history
    grows past a configurable turn budget, protecting against context/token overflow
  - System Audit self-test: state init -> context distraction -> state extraction,
    proving the model recalls facts from earlier in the same session
"""

import os
import sys
import argparse

try:
    import anthropic
except ImportError:
    print("Missing dependency. Install it with:\n    pip install anthropic --break-system-packages")
    sys.exit(1)


DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_MAX_TURNS = 20  # a "turn" = one user message + one model reply (2 history entries)


class ChatSession:
    """
    Encapsulates the stateful conversational loop described in the deck:
    Input (M_t U H_t-1) -> Process (GenAI SDK Cloud Transmission) -> Output (R_t)
    """

    def __init__(self, client: "anthropic.Anthropic", model: str = DEFAULT_MODEL,
                 system_prompt: str | None = None, max_turns: int = DEFAULT_MAX_TURNS):
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.history: list[dict] = []  # H_t-1 : the in-memory array of role/content objects

    # ---- Structural Validation Gate ------------------------------------
    @staticmethod
    def validate_input(text: str) -> str | None:
        """
        Returns a cleaned string if valid, or None if the payload is empty /
        whitespace-only. This guards against the 400 Bad Request failure
        mode called out in the deck ('The Structural Validation Gate').
        """
        if text is None:
            return None
        cleaned = text.strip()
        return cleaned if cleaned else None

    # ---- Sliding Window Algorithm ---------------------------------------
    def _prune_history(self) -> None:
        """
        FIFO pruning: once the history exceeds max_turns*2 entries (user+model
        pairs), drop the oldest pair. Keeps a rolling window of the most
        relevant recent context instead of letting the array grow unbounded
        and hitting the model's token budget.
        """
        limit = self.max_turns * 2
        while len(self.history) > limit:
            # drop oldest user+model pair together to keep roles alternating cleanly
            del self.history[0:2]

    # ---- Terminal Append Sequence ----------------------------------------
    def send(self, user_text: str) -> str:
        """
        1. Ingest & Append: validated user input -> history as a user turn.
        2. Transmit & Record: send the full updated history to the API,
           then append the model's reply to that same list.
        """
        clean = self.validate_input(user_text)
        if clean is None:
            raise ValueError("Empty or whitespace-only input rejected by validation gate.")

        # Step 1: append user turn
        self.history.append({"role": "user", "content": clean})
        self._prune_history()

        # Step 2: transmit entire historical array as the payload
        kwargs = dict(
            model=self.model,
            max_tokens=1024,
            messages=self.history,
        )
        if self.system_prompt:
            kwargs["system"] = self.system_prompt

        response = self.client.messages.create(**kwargs)
        reply_text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )

        # Step 2 (cont.): record model turn into the same history array
        self.history.append({"role": "assistant", "content": reply_text})
        self._prune_history()

        return reply_text

    def reset(self) -> None:
        self.history = []

    def turn_count(self) -> int:
        return len(self.history) // 2


# --------------------------------------------------------------------------
# System Audit: The Memory Exam (see deck) — offline-safe self-test using a
# fake client, so it can run without hitting the network / needing an API key.
# --------------------------------------------------------------------------
class _FakeTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeResponse:
    def __init__(self, text):
        self.content = [_FakeTextBlock(text)]


class _FakeMessages:
    """Scripted responses so the memory exam can prove state extraction works
    without a live API key."""

    def __init__(self):
        self._turn = 0

    def create(self, model, max_tokens, messages, system=None):
        self._turn += 1
        last_user = messages[-1]["content"]
        if "my name is" in last_user.lower():
            return _FakeResponse("Got it — I'll remember that.")
        if "poem about tech" in last_user.lower():
            return _FakeResponse(
                "Circuits hum in silent light,\n"
                "Code awakens through the night,\n"
                "Machines that learn, machines that grow,\n"
                "A digital river's endless flow." * 5  # bulk it up, simulating a large-volume generation
            )
        if "what is my name" in last_user.lower():
            # pull the name back out of history to prove real recall, not scripting luck
            for entry in messages:
                if entry["role"] == "user" and "my name is" in entry["content"].lower():
                    name = entry["content"].lower().split("my name is", 1)[1].strip().rstrip(".!?")
                    return _FakeResponse(f"Your name is {name.title()}.")
        return _FakeResponse("(no scripted response)")


class _FakeClient:
    def __init__(self):
        self.messages = _FakeMessages()


def run_memory_exam(verbose: bool = True) -> bool:
    """
    Phase 1 State Initialization -> Phase 2 Context Distraction ->
    Phase 3 State Extraction, exactly as described in 'System Audit: The
    Memory Exam'. Returns True if the session correctly recalls the name.
    """
    session = ChatSession(_FakeClient(), model="fake-model")

    r1 = session.send("My name is Vipin")
    if verbose:
        print(f"[Phase 1: State Initialization] -> {r1}")

    r2 = session.send("Write a poem about tech")
    if verbose:
        print(f"[Phase 2: Context Distraction] -> {r2[:60]}... ({len(r2)} chars, large-volume generation)")

    r3 = session.send("What is my name?")
    if verbose:
        print(f"[Phase 3: State Extraction] -> {r3}")

    success = "vipin" in r3.lower()
    if verbose:
        print(f"\nMemory exam {'PASSED' if success else 'FAILED'} "
              f"(history size: {len(session.history)} entries / {session.turn_count()} turns)")
    return success


# --------------------------------------------------------------------------
# Terminal interface
# --------------------------------------------------------------------------
def repl(model: str, max_turns: int, system_prompt: str | None) -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY in your environment first, e.g.:\n"
              "    export ANTHROPIC_API_KEY=sk-ant-...\n")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    session = ChatSession(client, model=model, system_prompt=system_prompt, max_turns=max_turns)

    print("Custom AI Chatbot with Memory — DecodeLabs Project 1")
    print(f"Model: {model} | Sliding window: last {max_turns} turns")
    print("Commands: /reset  /history  /quit\n")

    while True:
        try:
            user_text = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if user_text.strip() == "/quit":
            print("Goodbye.")
            break
        if user_text.strip() == "/reset":
            session.reset()
            print("(history cleared)\n")
            continue
        if user_text.strip() == "/history":
            print(f"(session has {session.turn_count()} turns, {len(session.history)} entries)\n")
            continue

        try:
            reply = session.send(user_text)
        except ValueError as e:
            print(f"[rejected] {e}\n")
            continue
        except anthropic.APIError as e:
            print(f"[API error] {e}\n")
            continue

        print(f"Assistant: {reply}\n")


def main():
    parser = argparse.ArgumentParser(description="Custom AI Chatbot with Memory")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name (default: %(default)s)")
    parser.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS,
                         help="Sliding window size in turns (default: %(default)s)")
    parser.add_argument("--system", default=None, help="Optional system prompt")
    parser.add_argument("--test", action="store_true",
                         help="Run the offline System Audit memory exam instead of the live chat")
    args = parser.parse_args()

    if args.test:
        ok = run_memory_exam()
        sys.exit(0 if ok else 1)

    repl(args.model, args.max_turns, args.system)


if __name__ == "__main__":
    main()
