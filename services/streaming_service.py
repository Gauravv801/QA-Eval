from script_1_gen import generate_fsm
import json


class StreamingService:
    def __init__(self, file_manager):
        self.file_manager = file_manager

    def stream_generation(self, system_prompt, user_message, thinking_callback=None, text_callback=None):
        """
        Wrapper around script_1_gen.generate_fsm with session-based file saving.

        Returns:
            tuple: (json_data_dict, cost_data_dict)

        Raises:
            ValueError: If response is empty or invalid JSON
            RuntimeError: If unexpected error occurs
        """
        try:
            # Call the original script function
            final_text, final_thinking, cost_data = generate_fsm(
                system_prompt,
                user_message,
                thinking_callback=thinking_callback,
                text_callback=text_callback
            )

            # Save raw response for debugging (before parsing)
            self.file_manager.save_text(final_text, 'raw_response.txt')

            # Parse JSON with error handling
            try:
                json_data = json.loads(final_text)
            except json.JSONDecodeError as e:
                # Save failed response for inspection
                error_msg = (
                    f"Failed to parse JSON from Claude's response.\n"
                    f"Error: {str(e)}\n"
                    f"Response length: {len(final_text)} chars\n"
                    f"Response preview:\n{final_text[:500]}..."
                )
                self.file_manager.save_text(error_msg, 'parsing_error.txt')
                raise ValueError(error_msg) from e

            # Save to session directory
            self.file_manager.save_json(json_data, 'output.json')
            self.file_manager.save_json(cost_data, 'cost_metrics.json')
            self.file_manager.save_text(final_thinking, 'thinking.txt')

            return json_data, cost_data

        except ValueError as e:
            # Re-raise validation errors from generate_fsm
            raise
        except Exception as e:
            # Catch any other unexpected errors
            raise RuntimeError(f"Unexpected error during FSM generation: {str(e)}") from e
