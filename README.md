# agent-skill-qa

Claude Code skills for QA testing — PR testing, staging validation, security checks with Playwright browser automation.

## Skills

| Skill | Description |
|-------|-------------|
| **qa-test-pr** | Comprehensive QA testing of a Pull Request on a staging environment — smoke, sanity, regression, security, IDOR, API, multi-role, and performance testing with Playwright browser automation and detailed reporting |

## Installation

```bash
# Add as a plugin marketplace
/plugin marketplace add reduanmasud/agent-skill-qa

# Install the plugin
/plugin install agent-skill-qa@reduanmasud-agent-skill-qa
```

## Usage

```bash
# QA test a pull request
/agent-skill-qa:qa-test-pr 4214
```

## Requirements

- Claude Code with Playwright MCP server configured
- SSH access to staging server
- GitHub CLI (`gh`) for PR analysis

## License

MIT
