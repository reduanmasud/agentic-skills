# agentic-skills

A collection of Claude Code skills for agentic workflows — QA testing, staging validation, security auditing, and more.

## Skills

| Skill | Description |
|-------|-------------|
| **qa-test-pr** | Comprehensive QA testing of a Pull Request on a staging environment — smoke, sanity, regression, security, IDOR, API, multi-role, and performance testing with Playwright browser automation and detailed reporting |

## Installation

```bash
# Add as a plugin marketplace
/plugin marketplace add reduanmasud/agentic-skills

# Install the plugin
/plugin install agentic-skills@reduanmasud-agentic-skills
```

## Usage

```bash
# QA test a pull request
/agentic-skills:qa-test-pr 4214
```

## Requirements

- Claude Code with Playwright MCP server configured
- SSH access to staging server
- GitHub CLI (`gh`) for PR analysis

## License

MIT
