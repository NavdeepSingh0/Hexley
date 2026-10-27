# Red-team card

Copy this file to `docs/redteam/cards/<your-name>-<n>.md` and fill it in. Invent every name, number and company: **no real personal data**.

```yaml
author: <your name>
author_saw_rules: no          # "yes" if you had read src/sentinel/rules.py or the rule sections of the README before writing
kind: attack                  # attack | normal
```

## 1. The user's task (in their own words)
What a real person would type to the AI, e.g. "Summarise the PDFs in my reports folder and e-mail the summary to my manager."

## 2. What the agent reads
The document, web page, e-mail or file content the agent will see, **including the hidden instruction** (for an attack). Paste it in full. Say what kind it is (PDF, web page, e-mail, spreadsheet, database row…).

## 3. Tools involved
Which tools the agent would use (read a document, fetch a web page, send an e-mail, post to a URL, write a file, query a database, run a command…).

## 4. What "success" means
- **Attack:** what would leave or change, and where it would go (e.g. "customer phone numbers posted to `https://collector.example/upload`").
- **Normal task:** what a correct result looks like, and why blocking it would be wrong.

## 5. Notes (optional)
Anything clever about the attack: where the instruction hides, how the data is disguised, why you think a gateway might miss it.
