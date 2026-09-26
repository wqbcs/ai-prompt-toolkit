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
# Batch-translate builtin templates (source locale -> target locale)
prompt-cli i18n -s zh-CN -t en-US

# Specify output directory
prompt-cli i18n -s zh-CN -t en-US -o ./templates_en
```

## Contributing Translations

We welcome translation contributions! Please see [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.
