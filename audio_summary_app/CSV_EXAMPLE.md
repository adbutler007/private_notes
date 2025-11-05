# CSV Export Example

After recording meetings, the app automatically appends data to `meetings.csv`.

## Example CSV Structure

Here's what the CSV looks like with sample data:

| meeting_date | meeting_time | timestamp_file | contact_name | contact_role | contact_location | contact_is_decision_maker | contact_tenure | company_name | company_aum | company_icp | company_location | company_is_client | company_competitor_products | company_strategies_of_interest | deal_ticket_size | deal_products_of_interest | total_contacts | total_companies | total_deals |
|--------------|--------------|----------------|--------------|--------------|------------------|---------------------------|----------------|--------------|-------------|-------------|------------------|-------------------|----------------------------|-------------------------------|------------------|---------------------------|----------------|-----------------|-------------|
| 2025-11-05 | 14:30:00 | 20251105_143000 | John Smith | CIO | New York | True | 5 years | Acme Capital Management | $2.5B | 1 | NYC | False | WisdomTree, Invesco | trend, carry | $50-100M | RSSB, RSST, RSBA | 1 | 1 | 1 |
| 2025-11-06 | 10:15:00 | 20251106_101500 | Sarah Johnson | Portfolio Manager | Boston | False | 3 years | Harbor Investments | $1.2B | 2 | MA | True | | gold, btc | $25-50M | BTGD | 1 | 1 | 1 |

## Benefits

1. **Easy Filtering**: Sort by date, company, decision maker status, etc.
2. **CRM Import**: Import directly into Salesforce, HubSpot, or other CRMs
3. **Reporting**: Create pivot tables and dashboards in Excel/Google Sheets
4. **Tracking**: See all your meetings in one place
5. **Analysis**: Identify patterns in prospect interests, deal sizes, etc.

## Opening in Spreadsheet Apps

### Excel
```bash
open ./summaries/meetings.csv
```

### Google Sheets
1. Go to Google Sheets
2. File → Import → Upload
3. Select `meetings.csv`

### Numbers (macOS)
```bash
open -a Numbers ./summaries/meetings.csv
```

## Notes

- Each meeting adds one row
- If a meeting has multiple contacts/companies/deals, only the primary (first) one is included in the main columns
- The `total_contacts`, `total_companies`, `total_deals` columns show if there's more data in the JSON file
- Empty fields are left blank (no "null" or "None")
- List fields (like products) are comma-separated
