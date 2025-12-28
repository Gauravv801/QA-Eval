# Deployment Guide

## Overview
This guide covers deploying the QA Eval app to **Streamlit Community Cloud** (free tier) with automatic deployment from GitHub.

## Prerequisites
- GitHub account
- Anthropic API key

## Local Setup (First Time)

### 1. Set up Streamlit secrets for local testing
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` and add your API key:
```toml
ANTHROPIC_API_KEY = "sk-ant-your-actual-key-here"
```

### 2. Test locally
```bash
streamlit run app.py
```

Verify everything works before deploying.

## GitHub Setup

### 1. Initialize Git repository
```bash
git init
git add .
git commit -m "Initial commit: QA Eval pipeline"
```

### 2. Create GitHub repository
1. Go to https://github.com/new
2. Name your repo (e.g., `qa-eval`)
3. Make it **private** if you want to keep it confidential
4. Don't initialize with README (already have files)
5. Click "Create repository"

### 3. Push to GitHub
```bash
git remote add origin https://github.com/YOUR_USERNAME/qa-eval.git
git branch -M main
git push -u origin main
```

## Streamlit Cloud Deployment

### 1. Deploy app
1. Go to https://share.streamlit.io/
2. Sign in with GitHub
3. Click **"New app"**
4. Configure:
   - **Repository:** YOUR_USERNAME/qa-eval
   - **Branch:** main
   - **Main file path:** app.py
   - **Python version:** 3.9 or higher

### 2. Configure secrets
1. Before clicking "Deploy", expand **"Advanced settings"**
2. Click **"Secrets"**
3. Paste your API key:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-your-actual-key-here"
   ```
4. Click **"Save"**

### 3. Deploy
1. Click **"Deploy!"**
2. Wait 2-5 minutes for initial deployment
3. Your app will be live at: `https://YOUR_USERNAME-qa-eval-XXXXX.streamlit.app`

## Making Updates (Auto-Deploy)

After initial setup, every push to `main` branch automatically redeploys:

```bash
# Make your changes
git add .
git commit -m "Description of changes"
git push
```

Changes go live in ~2 minutes. Watch deployment status at https://share.streamlit.io/

## Important Notes

### ⚠️ Ephemeral File Storage
Streamlit Cloud has **ephemeral filesystem** - files in `outputs/` and `history/` directories are wiped on:
- App restart
- Redeployment
- Platform maintenance

**Impact:**
- Run history is temporary (lost on each deploy)
- Session outputs only persist during app lifecycle

**Solution options:**
- Accept temporary storage (simplest for MVP)
- Add cloud storage (S3/GCS) for persistence (requires code changes)
- Use database instead of JSON files (requires architecture changes)

### Free Tier Limitations
- **Sleep after inactivity:** App sleeps after 7 days without traffic
- **Resources:** 1 CPU core, 800MB RAM
- **Visibility:** Public by default (upgrade to Teams for private apps)
- **Build time:** ~2-5 minutes per deploy

### Managing Secrets
**NEVER commit these files:**
- `.env` (excluded by `.gitignore`)
- `.streamlit/secrets.toml` (excluded by `.gitignore`)

**To update API key on Streamlit Cloud:**
1. Go to https://share.streamlit.io/
2. Select your app
3. Click **Settings** > **Secrets**
4. Update and save
5. App auto-restarts with new secrets

## Troubleshooting

### App won't start
- Check logs in Streamlit Cloud dashboard
- Verify `ANTHROPIC_API_KEY` is set in Secrets
- Ensure `packages.txt` includes `graphviz`

### Graphviz errors
- Confirm `packages.txt` exists with `graphviz` entry
- Streamlit Cloud should auto-install system dependency

### API key not working
- Double-check secret name is exactly `ANTHROPIC_API_KEY`
- No quotes needed in Streamlit secrets UI (just the key value)
- Restart app after changing secrets

### Changes not deploying
- Check GitHub push succeeded: `git push origin main`
- Verify branch is `main` (not `master`)
- Check deployment logs at https://share.streamlit.io/

## Local vs Cloud Differences

| Feature | Local | Streamlit Cloud |
|---------|-------|-----------------|
| API Key Source | `.env` file | Streamlit secrets |
| File Persistence | Permanent | Ephemeral |
| URL | localhost:8501 | Public URL |
| Deployment | Manual run | Auto on git push |

## Monitoring Costs

The app uses Claude Opus 4.5 ($5/1M input, $25/1M output tokens). Monitor usage:
- Cost metrics shown in app after each run
- Check Anthropic Console: https://console.anthropic.com/
- Set up usage alerts in Anthropic dashboard

## Getting Help

- **Streamlit Cloud Issues:** https://discuss.streamlit.io/
- **App Issues:** Check app logs in Streamlit Cloud dashboard
- **API Issues:** https://console.anthropic.com/
