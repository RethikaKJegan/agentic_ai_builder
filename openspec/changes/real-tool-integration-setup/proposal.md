# Real tool integration setup

Configure twelve provider integrations in the project-local .env, preserving existing values. Start with public read-only APIs, then configure authenticated providers only when credentials can be obtained through authorized workflows. Reuse one Google project and desktop OAuth client for Sheets, Drive, Calendar, and Docs.

This change provides configuration, secret-safe validation, local webhook verification, and manual setup instructions. It does not implement the Tool Registry or runtime, alter shared contracts, send messages, enable billing, or register external webhooks.
