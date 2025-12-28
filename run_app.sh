#!/bin/bash
# Quick launcher for QA Evaluation Pipeline Streamlit App
cd /Users/gaurav.maniyar/QA_Eval
echo "Starting QA Evaluation Pipeline on port 8503..."
python3 -m streamlit run app.py --server.port 8503
