# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

Including:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Scope

This policy covers:
- The Home Assistant add-on code in this repository
- Docker image build and runtime configuration
- Handling of API keys and session data

## Known Considerations

- **API keys** are provided at runtime via Home Assistant configuration and exported as environment variables within the container. They are never written to disk or committed to version control.
- **Full-auto mode** grants Codex the ability to execute arbitrary commands within the container. This is by design but should be used with caution.
- **Session data** stored in `/data/.codex-sessions` may contain sensitive conversation history.
