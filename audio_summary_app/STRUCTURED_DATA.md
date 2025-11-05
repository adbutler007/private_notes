# Structured Data Extraction

The audio summary app now automatically extracts structured meeting intelligence from your recordings.

## What Gets Extracted

After each recording, the app generates **three outputs**:

1. `summary_YYYYMMDD_HHMMSS.txt` - Human-readable summary
2. `summary_YYYYMMDD_HHMMSS.json` - Structured data in JSON format
3. `meetings.csv` - Cumulative CSV with all meeting data (one row per meeting)

## Data Schema

The JSON file contains three main sections:

### Contact Data
- `name`: Full name of the contact
- `role`: Job title or role
- `location`: Geographic location
- `is_decision_maker`: Whether they are a decision maker (boolean)
- `tenure_duration`: Duration in current position

### Company Data
- `name`: Company name
- `aum`: Assets Under Management
- `icp_classification`: ICP classification (1 or 2)
- `location`: Geographic location
- `is_client`: Whether they are currently a client (boolean)
- `competitor_products`: List of competitor products they hold
- `strategies_of_interest`: List of strategies (trend, carry, m.arb, gold, btc)

### Deal Data
- `ticket_size`: Possible investment ticket size
- `products_of_interest`: List of products (RSSB, RSST, RSBT, RSSY, RSBY, RSSX, RSBA, BTGD)

## Example Output

```json
{
  "contacts": [
    {
      "name": "John Smith",
      "role": "CIO",
      "location": "New York",
      "is_decision_maker": true,
      "tenure_duration": "5 years"
    }
  ],
  "companies": [
    {
      "name": "Acme Capital Management",
      "aum": "$2.5B",
      "icp_classification": 1,
      "location": "NYC",
      "is_client": false,
      "competitor_products": ["WisdomTree", "Invesco"],
      "strategies_of_interest": ["trend", "carry"]
    }
  ],
  "deals": [
    {
      "ticket_size": "$50-100M",
      "products_of_interest": ["RSSB", "RSST", "RSBA"]
    }
  ]
}
```

## How It Works

1. **During Recording**: Chunk summaries (every 5 minutes) are instructed to extract this information if mentioned
2. **After Recording**: A second LLM call uses Ollama's structured output feature to extract all data from the chunk summaries into the JSON schema
3. **Privacy**: The extraction happens on-device using Ollama (no data sent to cloud)

## Customization

You can customize the extraction by editing the prompts in `config.py`:

- `chunk_summary_prompt`: Instructions for what to extract during chunk summarization
- `data_extraction_prompt`: Instructions for the final structured extraction

The schema is defined in `summarizer.py` using Pydantic models (ContactData, CompanyData, DealData, MeetingData).

## CSV Export

The `meetings.csv` file contains one row per meeting with the following columns:

- **Meeting Info**: `meeting_date`, `meeting_time`, `timestamp_file`
- **Contact**: `contact_name`, `contact_role`, `contact_location`, `contact_is_decision_maker`, `contact_tenure`
- **Company**: `company_name`, `company_aum`, `company_icp`, `company_location`, `company_is_client`, `company_competitor_products`, `company_strategies_of_interest`
- **Deal**: `deal_ticket_size`, `deal_products_of_interest`
- **Counts**: `total_contacts`, `total_companies`, `total_deals`

The CSV file is perfect for:
- Tracking all meetings in a spreadsheet (Excel, Google Sheets, Numbers)
- Importing into CRM systems
- Creating reports and dashboards
- Quick filtering and sorting of meeting data

### CSV Configuration

You can customize the CSV path in `config.py`:

```python
csv_export_path: str = "./summaries/meetings.csv"
```

## Usage

No changes needed to your workflow - just use the app normally:

```bash
uv run python -m audio_summary_app
> start
# ... your meeting ...
> stop
```

All files are automatically saved to `./summaries/`:
- `summary_YYYYMMDD_HHMMSS.txt` (text summary)
- `summary_YYYYMMDD_HHMMSS.json` (structured JSON)
- `meetings.csv` (cumulative spreadsheet - new row appended)
