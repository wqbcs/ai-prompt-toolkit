# English Documentation

This directory contains English translations of project documentation.

## Available Documentation

| Document | Chinese Original | Status |
|----------|-----------------|--------|
| README.md | ./README.md | Pending |
| CHANGELOG.md | ./CHANGELOG.md | Pending |

## i18n Support

The toolkit supports internationalization via the `prompt-cli i18n` command:

```bash
# Translate a prompt to English
prompt-cli i18n -s prompt_zh.md --target-lang en

# Translate with glossary
prompt-cli i18n -s prompt_zh.md --target-lang en --glossary _i18n/glossary.json
```

## Contributing Translations

We welcome translation contributions! Please see [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.
