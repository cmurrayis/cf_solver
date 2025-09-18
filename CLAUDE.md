# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CF_Solver is a specification-driven development project that uses a structured workflow for feature planning, design, and implementation. The project follows a constitutional development approach with automated templates and PowerShell scripts for workflow management.

## Key Commands

### Specification Workflow Commands
- `/specify "feature description"` - Create feature specification from natural language description
- `/plan` - Generate implementation plan from feature specification
- `/tasks` - Generate actionable task list from design artifacts

### PowerShell Scripts
Located in `.specify/scripts/powershell/`:
- `create-new-feature.ps1` - Creates new feature branch and spec file
- `setup-plan.ps1` - Sets up implementation planning workflow
- `check-task-prerequisites.ps1` - Validates prerequisites for task generation
- `update-agent-context.ps1` - Updates AI assistant context files

## Architecture

### Directory Structure

```
.specify/
â”œâ”€â”€ scripts/powershell/     # Workflow automation scripts
â”œâ”€â”€ templates/              # Template files for specifications
â”‚   â”œâ”€â”€ spec-template.md   # Feature specification template
â”‚   â”œâ”€â”€ plan-template.md   # Implementation plan template
â”‚   â”œâ”€â”€ tasks-template.md  # Task generation template
â”‚   â””â”€â”€ agent-file-template.md  # AI assistant context template
â””â”€â”€ memory/                # Constitutional requirements and constraints

.claude/
â”œâ”€â”€ commands/              # Claude Code custom commands
â”‚   â”œâ”€â”€ specify.md        # /specify command definition
â”‚   â”œâ”€â”€ plan.md          # /plan command definition
â”‚   â””â”€â”€ tasks.md         # /tasks command definition
â””â”€â”€ settings.local.json   # Claude permissions configuration

specs/[###-feature]/       # Generated per feature
â”œâ”€â”€ spec.md               # Feature specification
â”œâ”€â”€ plan.md              # Implementation plan
â”œâ”€â”€ research.md          # Technical research
â”œâ”€â”€ data-model.md        # Data model design
â”œâ”€â”€ quickstart.md        # Test scenarios
â”œâ”€â”€ contracts/           # API contracts
â””â”€â”€ tasks.md            # Actionable task list
```

### Development Workflow

1. **Feature Specification** (`/specify`) - Convert natural language to structured spec
2. **Implementation Planning** (`/plan`) - Generate technical design and research
3. **Task Generation** (`/tasks`) - Create ordered, executable task list
4. **Implementation** - Execute tasks following constitutional principles
5. **Validation** - Run tests and verify requirements

### Constitutional Development

The project follows constitutional principles stored in `.specify/memory/constitution.md`. Key principles include:
- Simplicity over complexity
- Test-driven development
- Clear separation of concerns
- Dependency-ordered implementation

### Template System

All specifications and plans use structured templates with:
- Mandatory and optional sections
- Execution flow definitions
- Gate checks and validation
- Progress tracking mechanisms

## File Patterns

- Feature branches: `###-feature-name` format
- Specification files: Follow template structure exactly
- Contract files: Use OpenAPI/GraphQL schemas
- Test files: One per contract, organized by type

## Development Notes

- All file paths must be absolute when working with PowerShell scripts
- Template execution is self-contained and follows defined flows
- Progress tracking is built into templates and should be updated during execution
- Constitutional violations must be documented and justified in complexity tracking tables
