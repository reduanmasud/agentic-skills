# agentic-skills

A collection of Claude Code skills for agentic workflows — QA testing, staging validation, security auditing, and more.

## Skills

| Skill | Description |
|-------|-------------|
| **xcloud-test** | Deep QA of an xCloud pull request on the xcdev lab: expected behaviour written before reading the code (oracle), a before/after comparison against the base branch, real servers and seeded roles, a silent-failure sentinel (logs, failed jobs, task exit codes), a black-box explorer, language checks across 20 locales, and a validated report. Falls back to a plain SSH staging server without the lab |

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

Remove the installed copy first: `cp -r` into an existing folder nests the new copy inside it and leaves deleted reference files behind.

```bash
git clone https://github.com/reduanmasud/agentic-skills.git /tmp/agentic-skills
rm -rf ~/.claude/skills/xcloud-test
cp -r /tmp/agentic-skills/skills/xcloud-test ~/.claude/skills/xcloud-test
rm -rf /tmp/agentic-skills
```

## Usage

Once installed, invoke the skill in Claude Code:

```
/xcloud-test 4214
/xcloud-test 4214 interactive
```

Where `4214` is the PR number you want to QA test. `interactive` hands the browser steps to you while the skill
checks the server around each one. Run state goes to `~/.xcloud-qa/pr<N>/`, outside the repository.

## Requirements

- **Claude Code** with the **xcdev MCP** connected (lab access: previews, servers, seeded accounts, page checks)
- **GitHub CLI** (`gh`) for PR analysis, and **python3**
- **Playwright** in the xCloud checkout's `node_modules` (for `scripts/lab-flow.mjs`, browser flows beyond `page_check`)
- Optional: the **xcloud-brain** MCP (product history and support tickets for the oracle)
- Without the lab: SSH access to a staging server (`references/staging-fallback.md`)

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
