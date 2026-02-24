# Obtaining API Keys

This guide walks first-time users through obtaining the API keys needed for mpv-scraper. TVDB and TMDB provide the best metadata quality; both offer free tiers for personal use.

## Overview

| Provider | Used For | Required? | Cost | Signup Link |
|----------|----------|-----------|------|--------------|
| **TVDB** | TV shows (episodes, posters, logos) | Yes (for TV) | Free* or paid | [thetvdb.com](https://thetvdb.com/api-information/signup) |
| **TMDB** | Movies (posters, descriptions, ratings) | Yes (for movies) | Free | [themoviedb.org](https://www.themoviedb.org/settings/api) |
| **OMDb** | Movie fallback (optional) | No | Free (1,000/day) | [omdbapi.com](https://www.omdbapi.com/apikey.aspx) |

**No keys?** You can still run with [fallback providers](FALLBACKS.md) (TVmaze for TV, OMDb for movies) using `--fallback-only` or `--prefer-fallback`.

---

## TVDB (TheTVDB API)

TVDB is the primary source for TV show metadata. mpv-scraper uses the **TVDB API v4**.

### Step 1: Create a TVDB Account

1. Go to [thetvdb.com/auth/register](https://thetvdb.com/auth/register)
2. Create an account with your email
3. Verify your email if required

### Step 2: Sign Up for an API Key

1. Log in at [thetvdb.com](https://thetvdb.com)
2. Go to [thetvdb.com/api-information/signup](https://thetvdb.com/api-information/signup)
3. Choose your tier:
   - **Company/Project Revenue < $50k/year**: Free (requires attribution)
   - **$50k–$250k/year**: $1,000/year
   - **$250k–$1M/year**: $10,000/year
   - **$1M+**: Contact sales
4. Fill in:
   - Company or Project Name
   - Description of your project and how you'll use the data
5. Click **Submit**

### Step 3: Get Your API Key

1. After approval, go to [thetvdb.com/dashboard](https://thetvdb.com/dashboard)
2. In the left menu under **Account**, click **API Keys**
3. In the **Developers** section, click **Create a v4 API Key**
4. Fill in:
   - Project Name
   - Project Description
   - Company Name
   - Company Email
   - Company Description
5. Choose funding method:
   - **End-User Subscriptions**: Users subscribe to TVDB and get a PIN; keys are auto-approved
   - **Negotiated Contract**: For commercial use; requires sales review
6. Agree to Terms of Service and click **Create Key**
7. Copy your API key (long string, typically 32+ characters)

### Step 4: Optional PIN (End-User Subscriptions)

If you use TVDB's subscription model, users get a PIN. Set it in your environment:

```bash
export TVDB_PIN="your_pin_here"
```

For personal use with a free API key, you typically **do not need** a PIN.

### Attribution Requirement

The free tier requires attribution. Display this to end users:

> Metadata provided by [TheTVDB](https://thetvdb.com). Please consider adding missing information or subscribing.

---

## TMDB (The Movie Database)

TMDB is the primary source for movie metadata. mpv-scraper uses the TMDB API.

### Step 1: Create a TMDB Account

1. Go to [themoviedb.org/signup](https://www.themoviedb.org/signup)
2. Create an account with your email and username
3. Verify your email if required

### Step 2: Request an API Key

1. Log in at [themoviedb.org](https://www.themoviedb.org)
2. Click your profile icon (top right) → **Settings**
3. In the left menu, click **API**
4. Under **Request an API Key**, choose **Developer**
5. Accept the terms of use
6. Fill in the application form:
   - **Application Name**: e.g. "mpv-scraper" or "Personal Media Library"
   - **Application URL**: Your personal site or `https://github.com/yourusername/mpv-scraper`
   - **Application Summary**: Brief description of your use case
7. Submit the form

### Step 3: Get Your API Key

1. After approval, go to [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)
2. Under **API Key (v3 auth)**, copy your **API Read Access Token** (starts with `eyJ...`) or **API Key** (shorter alphanumeric string)
3. mpv-scraper accepts either format

### Important Notes

- **Use a desktop browser** – The API registration process is not optimized for mobile
- **Free for non-commercial use** – Commercial projects need to contact [sales@themoviedb.org](mailto:sales@themoviedb.org)
- **Attribution** – Display: "This product uses the TMDB API but is not endorsed or certified by TMDB"

---

## OMDb (Optional Fallback)

OMDb is an optional fallback for movies when TMDB fails or is unavailable.

### Step 1: Request a Free API Key

1. Go to [omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx)
2. Choose **FREE** (1,000 requests per day)
3. Enter your email address
4. Optionally sign up via Patreon for higher limits
5. Submit the form

### Step 2: Activate Your Key

1. Check your email for the API key
2. **Note**: Delivery can be delayed (especially with Yahoo, Outlook, Hotmail). If you don't receive it within an hour, contact the site owner
3. Click the activation link in the email if provided

### Step 3: Use in mpv-scraper

Set the optional environment variable:

```bash
export OMDB_API_KEY="your_omdb_key"
```

OMDb is used automatically when TMDB fails or when you run with `--fallback-only` or `--prefer-fallback`.

---

## Configuring Keys in mpv-scraper

### Option 1: Environment Variables

```bash
export TVDB_API_KEY="your_tvdb_api_key"
export TVDB_API_KEY2="your_tvdb_api_key"   # v4 key; TVDB_API_KEY also works
export TMDB_API_KEY="your_tmdb_api_key"
export OMDB_API_KEY="your_omdb_key"        # optional
```

### Option 2: .env File (Recommended)

Create a `.env` file in your library root (or project root):

```bash
# After running: mpv-scraper init /path/to/mpv
# Edit /path/to/mpv/.env

TVDB_API_KEY=your_tvdb_api_key_here
TVDB_API_KEY2=your_tvdb_api_key_here
TMDB_API_KEY=your_tmdb_api_key_here
# Optional:
OMDB_API_KEY=your_omdb_key_here
```

The scraper loads `.env` automatically via `python-dotenv`.

### Option 3: Persistent Shell Profile

Add to `~/.zshrc` (or `~/.bashrc`):

```bash
export TVDB_API_KEY="your_key"
export TMDB_API_KEY="your_key"
```

Then run `source ~/.zshrc` or open a new terminal.

### Verify Your Setup

```bash
# Quick check
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('TVDB_API_KEY:', 'SET' if os.getenv('TVDB_API_KEY') or os.getenv('TVDB_API_KEY2') else 'NOT SET')
print('TMDB_API_KEY:', 'SET' if os.getenv('TMDB_API_KEY') else 'NOT SET')
print('OMDB_API_KEY:', 'SET' if os.getenv('OMDB_API_KEY') else 'NOT SET (optional)')
"
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **401 Unauthorized** | Key is invalid or expired. Generate a new key from the provider dashboard |
| **TVDB: "API key not set"** | Use `TVDB_API_KEY` or `TVDB_API_KEY2`. Both work with v4 API |
| **Keys not loading** | Ensure `.env` is in the same directory as your library, or set variables before running |
| **TMDB: "Invalid API key"** | Use the API Key (v3) from the TMDB settings page, not the Request Token |
| **No keys at all** | Use [fallback mode](FALLBACKS.md) with `--fallback-only` |

For more help, see [API Troubleshooting](../technical/API_TROUBLESHOOTING.md).

---

## Quick Reference

| Variable | Provider | Required |
|----------|----------|----------|
| `TVDB_API_KEY` or `TVDB_API_KEY2` | TheTVDB | For TV shows |
| `TVDB_PIN` | TheTVDB | Only if using subscription model |
| `TMDB_API_KEY` | The Movie Database | For movies |
| `OMDB_API_KEY` | OMDb | Optional movie fallback |

---

**Next steps:** [Quick Start Guide](QUICK_START.md) | [Fallback Providers](FALLBACKS.md) | [API Troubleshooting](../technical/API_TROUBLESHOOTING.md)
