# AGENTS.md

This project was built collaboratively with Claude Code (Claude Opus 4.5), Anthropic's AI coding assistant.

## Development Process

The entire application was developed through conversational prompts, with Claude handling:

1. **Architecture Design**: Proposed the full-stack architecture with FastAPI + React + SQLite
2. **Backend Implementation**: Created all Python modules including the OAI-PMH collector
3. **Frontend Development**: Built React components with Recharts visualizations
4. **Debugging**: Identified and fixed the arXiv API issue (HTTP → HTTPS, Search API → OAI-PMH)
5. **Reliability Engineering**: Added retry logic, checkpointing, and logging for overnight syncs

## Key AI Contributions

### Problem Solving
- Diagnosed why arXiv Search API was returning 500 errors (date query format not supported)
- Pivoted to OAI-PMH protocol which properly supports date-based metadata harvesting
- Implemented batch fetching by parent category to reduce API calls

### Code Quality
- Added exponential backoff retry logic
- Implemented checkpoint/resume capability for long-running syncs
- Created comprehensive test suite before production runs

### DevOps
- Set up proper logging to files for overnight monitoring
- Configured nohup for terminal-independent execution
- Provided clear instructions for deployment and monitoring

## Session Statistics

- **Models Used**: Claude Opus 4.5
- **Primary Tools**: Write, Edit, Bash, Read, Grep
- **Files Created**: 15+
- **Iterations**: Multiple debugging cycles for API compatibility

## Prompting Patterns That Worked Well

1. **High-level requirements first**: "Build an arXiv trends dashboard with FastAPI backend and React frontend"
2. **Iterative debugging**: "Quick sync didn't work, check the database"
3. **Explicit constraints**: "Implement reliability improvements but don't start the sync yet"
4. **Clear sequencing**: "Start the sync, then remove the sync buttons from frontend"

## Lessons Learned

- arXiv's Search API doesn't support date range queries reliably; OAI-PMH is the proper protocol for metadata harvesting
- Always test with real API calls before building full sync logic
- Checkpoint systems are essential for long-running data collection tasks

---

*Built with [Claude Code](https://claude.ai/claude-code)*
