# LeadSite Pro

**Local Business Lead Generation & AI Website Builder**

A full-stack dashboard that discovers local businesses with weak web presence, ranks them by opportunity value, generates AI-powered mockup websites, and drafts personalized outreach emails — all from one interface.

## How It Works

1. **Discover** — Scan any area for businesses using Google Places API. Filter by category (restaurants, plumbers, dentists, etc.) and radius.
2. **Audit** — Automatically analyze each business's website for 14 quality checks across 7 categories: SSL, mobile-friendliness, page speed, SEO basics, structured data, social presence, and freshness. Businesses with no website score 0 (highest opportunity).
3. **Rank** — An Opportunity Score (0-100) combines Category Value Weight (40%), Website Deficiency (30%), Review Signal (15%), and Competition Gap (15%). Category weights are fully configurable.
4. **Scrape** — Enrich top prospects with Yelp data: reviews, hours, services, photos, and owner info. Also scrapes their existing website for branding (colors, logo, social links).
5. **Build** — Generate a complete, responsive single-page HTML website using OpenAI. Includes hero, about, services grid, testimonials from real reviews, contact section, and Google Map embed. Edit with code or natural language AI instructions.
6. **Outreach** — Draft personalized cold emails with AI. Each email references their specific web gaps, includes a mockup preview, shows your pricing tiers, and ends with a CTA. Send via SMTP or export.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy (async), SQLite |
| Frontend | React 18, Vite, Tailwind CSS, Lucide icons |
| AI | OpenAI GPT-4 / GPT-3.5 (configurable) |
| APIs | Google Places, Yelp Fusion, SMTP |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- API keys (see Configuration below)

### Setup

```bash
# Clone the repo
git clone https://github.com/jayryuki3/leadsite-pro.git
cd leadsite-pro

# Run the setup script (installs Python + Node dependencies)
chmod +x setup.sh
./setup.sh
```

### Run

```bash
# Start both backend (port 8000) and frontend (port 5173)
chmod +x start.sh
./start.sh
```

Open **http://localhost:5173** in your browser.

### Manual Setup (if scripts don't work)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

## Configuration

All API keys are configured through the **Settings** page in the app (http://localhost:5173/settings). Nothing goes in `.env` files.

### Required API Keys

| Key | Purpose | Get it at |
|-----|---------|----------|
| **OpenAI API Key** | AI mockup generation, email drafting, audit analysis | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| **Google Places API Key** | Business discovery and location search | [console.cloud.google.com](https://console.cloud.google.com/apis/library/places-backend.googleapis.com) |

### Optional API Keys

| Key | Purpose | Get it at |
|-----|---------|----------|
| **Yelp API Key** | Business enrichment (reviews, hours, photos) | [fusion.yelp.com](https://fusion.yelp.com/) |

### SMTP Configuration (for sending emails)

Configure in Settings under "Email / SMTP":
- SMTP Host (e.g., `smtp.gmail.com`)
- SMTP Port (default: 587)
- Username & Password
- From Name & Email

For Gmail: use an [App Password](https://myaccount.google.com/apppasswords), not your regular password.

### Other Settings

- **Business Info** — Your company name, email, phone, Calendly link (used in outreach emails)
- **Pricing Tiers** — Customize your service packages and prices (shown in emails)
- **Category Weights** — Adjust opportunity scoring per business category
- **OpenAI Model** — Switch between gpt-4, gpt-4-turbo, gpt-3.5-turbo

## Project Structure

```
leadsite-pro/
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── database.py             # Async SQLite + SQLAlchemy setup
│   ├── models/
│   │   ├── lead.py             # Lead + LeadDetail models
│   │   ├── mockup.py           # Mockup model
│   │   ├── email_draft.py      # Email draft model
│   │   ├── activity.py         # Activity tracking model
│   │   └── settings.py         # App settings model
│   ├── routes/
│   │   ├── leads.py            # Discovery, CRUD, ranking, scraping
│   │   ├── audit.py            # 14-check website quality audit
│   │   ├── mockups.py          # AI mockup generation & editing
│   │   ├── emails.py           # Email drafting, batch, SMTP send
│   │   ├── settings.py         # Settings CRUD, pricing tiers
│   │   ├── ai.py               # OpenAI integration
│   │   └── dashboard.py        # Pipeline stats & activity feed
│   ├── services/
│   │   ├── scraper.py          # Yelp + website content scraper
│   │   └── encryption.py       # API key encryption at rest
│   ├── requirements.txt
│   └── mockups/                # Generated HTML mockups (gitignored)
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Root component with routing
│   │   ├── main.jsx            # React entry point
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx   # Pipeline command center
│   │   │   ├── Discover.jsx    # Business discovery + scanning
│   │   │   ├── Leads.jsx       # Ranked leads table
│   │   │   ├── MockupBuilder.jsx # AI website editor + preview
│   │   │   ├── Outreach.jsx    # Email drafting & sending
│   │   │   └── Settings.jsx    # App configuration
│   │   ├── components/
│   │   │   └── Sidebar.jsx     # Navigation sidebar
│   │   └── api/
│   │       └── client.js       # Axios API client
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── setup.sh                    # First-time installation
├── start.sh                    # Launch both servers
└── README.md
```

## API Endpoints

### Leads
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/leads/discover` | Scan area for businesses |
| GET | `/leads` | List leads (sortable, filterable, paginated) |
| GET | `/leads/{id}` | Get lead details |
| PUT | `/leads/{id}` | Update lead |
| DELETE | `/leads/{id}` | Delete lead |
| POST | `/leads/{id}/scrape` | Enrich with Yelp + website data |
| POST | `/leads/rank` | Recalculate all opportunity scores |

### Audit
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/audit/{id}` | Run website quality audit |
| POST | `/audit/batch` | Audit multiple leads |
| POST | `/audit/{id}/ai-analysis` | AI explanation of audit results |

### Mockups
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/mockups/generate/{lead_id}` | Generate AI website mockup |
| GET | `/mockups` | List all mockups |
| GET | `/mockups/{id}` | Get mockup with HTML content |
| PUT | `/mockups/{id}` | Update HTML manually |
| POST | `/mockups/{id}/ai-edit` | AI-powered natural language edit |
| DELETE | `/mockups/{id}` | Delete mockup |

### Emails
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/emails/generate/{lead_id}` | Draft personalized email |
| POST | `/emails/batch-generate` | Batch draft for multiple leads |
| GET | `/emails` | List all drafts |
| GET | `/emails/{id}` | Get draft details |
| PUT | `/emails/{id}` | Edit draft |
| POST | `/emails/{id}/send` | Send via SMTP |
| DELETE | `/emails/{id}` | Delete draft |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/stats` | Pipeline funnel stats |
| GET | `/dashboard/activity` | Recent activity feed |
| GET | `/dashboard/revenue` | Revenue tracking |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/settings` | Get all settings |
| POST | `/settings` | Create/update setting |
| GET | `/settings/pricing-tiers` | Get pricing tiers |
| POST | `/settings/pricing-tiers` | Update pricing tiers |
| POST | `/settings/test-api-key` | Verify API key works |

## Pricing Strategy

Default tiers (customizable in Settings):

| Tier | Price | Includes |
|------|-------|----------|
| **Starter** | $497 | Single-page responsive site, contact form, Google Maps, basic SEO, 1 revision |
| **Professional** | $997 | Multi-page site, booking integration, 3 revisions, Google Business optimization |
| **Premium** | $1,997 | Custom design, e-commerce ready, ongoing SEO, social media setup, 5 revisions |
| **Retainer** | $197/mo | Monthly maintenance, content updates, analytics reports, priority support |

## Opportunity Scoring

The ranking algorithm weighs four factors:

- **Category Value (40%)** — Configurable per category. High-margin services (electricians, plumbers, lawyers) default to 90-95; low-margin (laundromats, gas stations) default to 25-40.
- **Website Deficiency (30%)** — Inverse of website quality score. No website = maximum opportunity.
- **Review Signal (15%)** — High review count + poor website = motivated business owner who invests in their business but neglects online presence.
- **Competition Gap (15%)** — How much better competitors' websites are in the same area and category.

## License

MIT
