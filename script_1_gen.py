# Code to call claude with the system and user prompt
import os
from dotenv import load_dotenv
from anthropic import Anthropic
import re
import json

# Try Streamlit secrets first, fallback to .env
try:
    import streamlit as st
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except:
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")

client = Anthropic(api_key=api_key)


def generate_fsm(system_prompt, user_message, thinking_callback=None, text_callback=None):
    """
    Core FSM generation logic with optional callbacks for UI integration.

    Args:
        system_prompt: System instructions for Claude
        user_message: User prompt to analyze
        thinking_callback: Optional function(chunk_text, full_thinking_text)
        text_callback: Optional function(chunk_text, full_text)

    Returns:
        tuple: (final_text, final_thinking, cost_data_dict)
    """
    final_thinking = ""
    final_text = ""

    with client.messages.stream(
        model="claude-opus-4-5-20251101",
        max_tokens=50000,
        thinking={
            "type": "enabled",
            "budget_tokens": 45000
        },
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    ) as stream:
        for event in stream:
            if event.type == "content_block_delta":
                if event.delta.type == "thinking_delta":
                    chunk = event.delta.thinking
                    final_thinking += chunk
                    if thinking_callback:
                        thinking_callback(chunk, final_thinking)
                elif event.delta.type == "text_delta":
                    chunk = event.delta.text
                    final_text += chunk
                    if text_callback:
                        text_callback(chunk, final_text)

        # Clean JSON from markdown blocks
        json_match = re.search(r"```(?:json)?\s*(.*)\s*```", final_text, re.DOTALL | re.IGNORECASE)
        if json_match:
            final_text = json_match.group(1).strip()
        else:
            final_text = final_text.strip()

        # Validate that we have content
        if not final_text:
            raise ValueError(
                "Claude returned empty text response. "
                "The model may have only generated thinking without text output. "
                f"Thinking length: {len(final_thinking)} chars"
            )

        # Validate JSON structure
        try:
            json.loads(final_text)  # Test parse (don't store result)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Claude's response is not valid JSON: {str(e)}\n"
                f"Response preview: {final_text[:200]}..."
            )

        # Calculate costs
        final_message = stream.get_final_message()
        input_tokens = final_message.usage.input_tokens
        output_tokens = final_message.usage.output_tokens

        price_per_million_input = 5.00
        price_per_million_output = 25.00

        input_cost = (input_tokens / 1_000_000) * price_per_million_input
        output_cost = (output_tokens / 1_000_000) * price_per_million_output
        total_cost = input_cost + output_cost

        cost_data = {
            "model": "claude-opus-4-5-20251101",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "total_cost_usd": round(total_cost, 6)
        }

        return final_text, final_thinking, cost_data


if __name__ == "__main__":
    # CLI execution - existing behavior preserved
    with open('prompt.txt', 'r') as file:
        content = file.read()

    # Ensure the separator exists to avoid errors
    if "---SEP---" in content:
        parts = content.split('---SEP---')
        system_prompt = parts[0].strip()
        user_message = parts[1].strip()
    else:
        print("Error: ---SEP--- delimiter not found in prompt.txt")
        exit()

    print("--- CLAUDE IS THINKING & RESPONDING ---")

    # Call the function with print callbacks
    final_text, final_thinking, cost_data = generate_fsm(
        system_prompt,
        user_message,
        thinking_callback=lambda chunk, full: print(chunk, end="", flush=True),
        text_callback=lambda chunk, full: print(chunk, end="", flush=True)
    )

    print("\n\n--- FINISHED ---")

    # Save outputs
    with open('output.json', 'w') as f:
        f.write(final_text)
        print("Response saved to output.json")

    with open('cost_metrics.json', 'w') as f:
        json.dump(cost_data, f, indent=4)
        print("Cost metrics saved to cost_metrics.json")

    print(f"\n--- COST CALCULATION ---")
    print(f"Input Tokens:  {cost_data['input_tokens']} (${cost_data['input_cost_usd']:.4f})")
    print(f"Output Tokens: {cost_data['output_tokens']} (${cost_data['output_cost_usd']:.4f})")
    print(f"Total Cost:    ${cost_data['total_cost_usd']:.4f}")