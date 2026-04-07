# Email Assistant - Harness Engineering Demo

A Python email assistant with GitHub Actions Harness Engineering.

## Project Structure

```
email-assistant/
├── .github/workflows/
│   ├── github-actions-demo.yml    # Test workflow
│   └── risk-policy-gate.yml       # Harness Engineering
├── harness/
│   └── risk-contract.json         # Risk configuration
├── src/
│   └── __init__.py
└── README.md
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run lint
flake8 src/
```

## Harness Engineering

This project uses Harness Engineering pattern:
- `risk-contract.json` defines risk tiers
- GitHub Actions automatically checks risk level on PR
- High-risk changes require additional review
