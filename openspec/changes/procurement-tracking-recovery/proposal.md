# Tracking creation recovery

## Why
The live tracking create ended with UNKNOWN_INVOCATION_RESULT and no returned resource ID. The operator checked Drive and reported the title absent. Existing transport suppresses the underlying error category, preventing diagnosis.

## What Changes
Preserve bounded HTTP failure categories and secret-checked messages in the private effect journal without complete provider bodies, headers, URLs or credentials. Correct creation metadata placement: spreadsheet metadata belongs at the root and sheet metadata belongs on its sheet. Add an authenticated operator-only tracking retry operation that archives the failed run and retry basis, refuses retry when a returned resource ID exists, and prepares a new exact gated action with a distinct setup key. Require an operator absence report or a journal-confirmed HTTP 400 rejection of that exact create. Keep the original intent frozen.

## Impact
Extension-only changes. No original application files or shared contracts change. No automatic uncertain-effect replay, self-decided action approval or mail send is added.
