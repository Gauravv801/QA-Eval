import subprocess
import shutil
import os
import sys
import time

# --- CONFIGURATION: Match these to your actual filenames ---
SCRIPT_1 = "script_1_gen.py"
SCRIPT_2 = "script_2_viz.py"
SCRIPT_3 = "script_3_ana.py"

def run_script(script_name):
    """Runs a python script as a subprocess, streaming output to the console."""
    print(f"\n{'='*60}")
    print(f">>> RUNNING: {script_name}")
    print(f"{'='*60}\n")

    if not os.path.exists(script_name):
        print(f"Error: Could not find file '{script_name}'")
        sys.exit(1)

    try:
        # check=True will raise an error if the script fails
        # capture_output=False ensures you see the 'Thinking' logs in real-time
        subprocess.run([sys.executable, script_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n!!! ERROR: {script_name} failed to run. Pipeline stopped.")
        sys.exit(1)

def bridge_files(source, destination):
    """Copies output from one step to match the input of the next."""
    if os.path.exists(source):
        shutil.copy(source, destination)
        print(f"\n[Pipeline Bridge] Copied '{source}' -> '{destination}'")
    else:
        print(f"\n[Pipeline Bridge] WARNING: Expected output '{source}' not found!")

# ==========================================
# MAIN PIPELINE EXECUTION
# ==========================================

if __name__ == "__main__":
    
    # --- STEP 1: GENERATION ---
    run_script(SCRIPT_1)
    
    # BRIDGE 1: Connect Script 1 (output.json) to Script 2 (LLM_output_axis.json)
    bridge_files("output.json", "LLM_output_axis.json")
    
    # --- STEP 2: VISUALIZATION ---
    # Note: Your script creates 'flowchart_claude' (source) and 'flowchart_claude.png' (image)
    run_script(SCRIPT_2)
    
    # BRIDGE 2: Connect Script 2 (flowchart_claude) to Script 3 (flowchart_collections_std)
    # We copy the source file (no extension) because Script 3 parses the text, not the PNG.
    bridge_files("flowchart_claude", "flowchart_collections_std")

    # --- STEP 3: ANALYSIS ---
    run_script(SCRIPT_3)

    print(f"\n{'='*60}")
    print(">>> PIPELINE COMPLETE")
    print(f"{'='*60}")