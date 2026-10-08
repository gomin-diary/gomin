# Agent Instructions

## Documentation

- Start with [docs/README.md](docs/README.md). Follow its index and read only the documents relevant to the task.
- Keep `docs/README.md` as the documentation index; update it when documents are added, moved, or removed.
- Keep this file in English, using concise headings and bullets. Do not duplicate the documentation index, detailed procedures, or project status here.
- Keep the root [README.md](README.md) limited to installation and running the project: essential commands, local addresses, restart and shutdown instructions, and relevant detail links.
- Do not add setup completion status, completed or pending work, Jira records, work history, architecture or stack details, deployment or CI/CD status, development rules, or a documentation index to the root README.
- Put detailed guidance in the appropriate document found through the documentation index; keep it consistent with the implementation.
- Follow [design document storage](docs/engineering/design-document-storage.md): keep local designs in Git-ignored `docs/superpowers/plans/` and publish them to the Confluence design database with their Jira work item.

## Secrets

- Never read, search the contents of, or print actual environment files such as `.env`, `.env.local`, `.env.production`, or their backups. Exclude them from content searches.
- For environment configuration, use `frontend/.env.example` and `backend/.env.example` only.
- Never expose keys, tokens, or passwords in output, documentation, or Jira. Do not dump environment variables or run commands that print credentials, including `supabase status` and its wrappers.

## Workflow

- Inspect `git status` and relevant diffs before editing. Preserve existing user changes.
- Verify facts against current code, configuration, and local Git history. Do not treat planned features as implemented or invent missing deployment details.
- Limit changes to the requested scope and use the relevant existing validation commands.
- For pull request creation or edits, use the [gomin-pr skill](.agents/skills/gomin-pr/SKILL.md) and follow [the PR writing guide](docs/engineering/pull-requests.md).
- Before reporting completion, check the diff, changed files, and affected documentation links. State what was verified and what remains unverified.

## Database Changes

- Follow [Supabase migration management](docs/engineering/database-migrations.md) for schema, permissions, and production data changes.
- Use a task branch and new SQL migrations; preserve shared or applied migration files.
- Keep local seed data separate from production migrations.
