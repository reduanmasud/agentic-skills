# agentic-skills

A collection of Claude Code skills for agentic workflows — QA testing, staging validation, security auditing, and more.

## Skills

| Skill | Description |
|-------|-------------|
| **xcloud-test** | Comprehensive QA testing of a Pull Request on a staging environment — smoke, sanity, regression, security, IDOR, API, multi-role, and performance testing with Playwright browser automation and detailed reporting |

## Installation

Claude Code skills can be installed at two scopes. Pick the one that fits your use case.

### Global (available in all projects)

Skills placed in `~/.claude/skills/` are available every time you use Claude Code, regardless of which project you're in.

```bash
# Clone the repo
git clone https://github.com/reduanmasud/agentic-skills.git /tmp/agentic-skills

# Copy the skill(s) you want
cp -r /tmp/agentic-skills/skills/xcloud-test ~/.claude/skills/xcloud-test

# Clean up
rm -rf /tmp/agentic-skills
```

Or as a one-liner:

```bash
git clone https://github.com/reduanmasud/agentic-skills.git /tmp/agentic-skills && cp -r /tmp/agentic-skills/skills/xcloud-test ~/.claude/skills/xcloud-test && rm -rf /tmp/agentic-skills
```

### Project-level (available in one project only)

Skills placed in `.claude/skills/` inside a project are only available when working in that project. This is useful if the skill is project-specific or you want to commit it to version control for your team.

```bash
# From your project root
mkdir -p .claude/skills

# Clone and copy
git clone https://github.com/reduanmasud/agentic-skills.git /tmp/agentic-skills
cp -r /tmp/agentic-skills/skills/xcloud-test .claude/skills/xcloud-test
rm -rf /tmp/agentic-skills
```

### Scope comparison

| Scope | Directory | Available in | Best for |
|-------|-----------|-------------|----------|
| **Global** | `~/.claude/skills/skill-name/` | All projects | Personal tools you use everywhere |
| **Project** | `.claude/skills/skill-name/` | That project only | Team-shared skills committed to git |

> **Note:** If a global and project skill share the same name, the project skill takes priority.

## Updating

To get the latest version of a skill, re-run the install steps — it will overwrite the existing `SKILL.md` with the latest version.

```bash
git clone https://github.com/reduanmasud/agentic-skills.git /tmp/agentic-skills
cp -r /tmp/agentic-skills/skills/xcloud-test ~/.claude/skills/xcloud-test
rm -rf /tmp/agentic-skills
```

## Usage

Once installed, invoke the skill in Claude Code:

```
/xcloud-test 4214
```

Where `4214` is the PR number you want to QA test.

## Requirements

- **Claude Code** with Playwright MCP server configured (for browser-based UI testing)
- **SSH access** to the staging server
- **GitHub CLI** (`gh`) for PR analysis

## Contributing

To add a new skill, create a directory under `skills/` with a `SKILL.md` file:

```
skills/
└── your-skill-name/
    └── SKILL.md
```

See the [Claude Code skills docs](https://docs.anthropic.com/en/docs/claude-code/skills) for the SKILL.md format.

## License

MIT
