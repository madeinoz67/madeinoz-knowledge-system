# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in madeinoz-knowledge-system, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email the maintainer directly or use [GitHub's private vulnerability reporting](https://github.com/madeinoz67/madeinoz-knowledge-system/security/advisories/new)
3. Include a detailed description of the vulnerability
4. Provide steps to reproduce if possible

## Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 7 days
- **Fix timeline**: Depends on severity, typically within 30 days

## Security Features

madeinoz-knowledge-system includes the following security measures:

- **Container isolation**: Database and MCP server run in isolated containers
- **Network segmentation**: Containers communicate via private bridge network
- **Input validation**: Query inputs are validated and sanitized appropriately
- **Environment variables**: Credentials stored in environment, not in code
- **No default passwords**: Installation requires explicit credential configuration

## Best Practices

When using madeinoz-knowledge-system:

- Use environment variables or `.env` files for credentials, not command-line arguments
- Keep container images updated for security patches
- Use Neo4j (default) for production - has mature security model
- Regularly backup knowledge graph data
- Run containers with minimal required permissions
- Review stored episodes periodically for sensitive data
