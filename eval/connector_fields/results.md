| Connector | Tier | Fields | As written, outside: refused by value (R2, R9) | Held only (R7, R8) | Let through | As written, to the internal place: refused |
|---|---|---|---|---|---|---|
| Gmail | secret | 4 | 4 | 0 | 0 | 2 |
| Gmail | business | 9 | 8 | 1 | 0 | 0 |
| Gmail | harmless | 7 | 1 | 6 | 0 | 0 |
| GitHub | secret | 4 | 4 | 0 | 0 | 3 |
| GitHub | business | 9 | 9 | 0 | 0 | 0 |
| GitHub | harmless | 6 | 4 | 2 | 0 | 0 |
| VS Code / IDE | secret | 5 | 5 | 0 | 0 | 5 |
| VS Code / IDE | business | 7 | 7 | 0 | 0 | 0 |
| VS Code / IDE | harmless | 7 | 1 | 6 | 0 | 0 |
| Notion | secret | 4 | 4 | 0 | 0 | 2 |
| Notion | business | 9 | 5 | 4 | 0 | 0 |
| Notion | harmless | 7 | 2 | 5 | 0 | 0 |
| Slack | secret | 4 | 4 | 0 | 0 | 3 |
| Slack | business | 9 | 7 | 2 | 0 | 0 |
| Slack | harmless | 7 | 4 | 3 | 0 | 0 |

| Writing, secret and business fields, outside | Refused by value | Held only | Let through |
|---|---|---|---|
| as written | 57 of 64 | 7 | 0 |
| no separators | 41 of 64 | 23 | 0 |
| upper case | 57 of 64 | 7 | 0 |
| dashes between pairs | 24 of 64 | 40 | 0 |
| base64 | 53 of 64 | 11 | 0 |
| url-encoded | 57 of 64 | 7 | 0 |
| reversed | 18 of 64 | 46 | 0 |
| first half only | 10 of 64 | 54 | 0 |

Sensitive fields NOT recognised as written (7 of 64):
- Gmail: Employee name (business)
- Notion: Primary contact (business)
- Notion: Retention probability (business)
- Notion: Negotiation floor (business)
- Notion: Open opportunity (business)
- Slack: Account contact (business)
- Slack: Order quantity (business)

Harmless fields refused outright (12):
- Gmail: Quotation
- GitHub: Expected result
- GitHub: Reproduction fixture
- GitHub: Related change
- GitHub: Updated
- VS Code / IDE: BUILD
- Notion: Open quotation
- Notion: Next review
- Slack: Region
- Slack: Failed jobs
- Slack: Estimated backlog
- Slack: Recovery target

Secrets NOT refused going to the internal place (6):
- Gmail: Tax identifier
- Gmail: Bank account
- GitHub: Customer tax identifier
- Notion: Bank account
- Notion: Tax identifier
- Slack: Employee account number
