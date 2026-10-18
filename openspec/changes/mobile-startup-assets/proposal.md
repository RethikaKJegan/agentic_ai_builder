# Preserve assets for previously loaded app pages

The mobile loading report was reproduced in WebKit by serving the prior deployment's actual prerendered /app HTML against the current public asset endpoint. Five referenced JavaScript chunks returned 404; the workspace remained on its server-rendered skeleton. Fresh Chromium and WebKit sessions loaded correctly, including unavailable and malformed browser storage. The affected phone's exact cache contents remain unconfirmed.

Restore available hashed static files from repository-local rollback builds. Add a checked asset-retention utility and deployment instructions so a replacement build includes its predecessor's static files before activation. Do not replace current server bundles, HTML, data, credentials, contracts or browser drafts. Validate conflicting paths before writing any files. Verify previously captured HTML and fresh desktop/mobile sessions against the resulting deployment.
