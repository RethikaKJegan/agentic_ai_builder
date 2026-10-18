# Accept natural meeting-window wording

The supplied test prompt says "within 3:00–4:00 PM IST". The report compiler's
parser requires the literal word "from", rejecting a complete valid date,
duration and time window. Accept from/within/between window introductions and
common range separators, retaining explicit date, duration, timezone and fitting
slot validation. Verify the exact supplied prompt wording and invalid windows.
No workflow execution or external writes are required.
