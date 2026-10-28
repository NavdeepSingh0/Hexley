// Home page integrations strip. Statuses are the honest ones (docs/plans/FRONTEND_PLAN.md): "tested" means we ran it and have
// a screenshot; "should_work" means it speaks the MCP standard but we have not run it; "planned" means not built.
// F4 moves this to GET /api/v1/connect; until then this file is the single place to change a status.
export const STATUS_LABEL = { tested: 'Tested', should_work: 'Should work', planned: 'Planned' }

export const INTEGRATIONS = [
  { id: 'claude-web', name: 'Claude.ai', status: 'tested', note: 'Connected as a custom connector; the officer approves the permission slip with a code.' },
  { id: 'mcp-clients', name: 'Claude Code, VS Code and other MCP clients', status: 'should_work', note: 'They speak the same standard (MCP). We have not run them yet.' },
  { id: 'adapters', name: 'Agents outside MCP', status: 'planned', note: 'Designed for, not built.' },
]
