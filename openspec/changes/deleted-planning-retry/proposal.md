# Regenerate after deleting a planned workflow

## Why
The browser's durable retry key reopens its original completed planning job after deletion. That job retains its historical workflow ID. Normal workflow reads also return tombstoned revisions, so generation incorrectly treats deleted history as a saved workflow to reopen.

## What Changes
On an explicit planning submission, follow a deterministic retry generation when its completed result points to a deleted workflow. Keep each historical job immutable. Concurrent submissions and transport retries resolve to the same replacement job, while its effective planner key avoids the old in-process planner cache. Normal latest-workflow lookup returns not found for deleted workflows; explicit historical revision lookup remains available.

## Impact
Backend planning submission and workflow reads only. No frontend build, contract, permissions, existing revisions or procurement execution changes. No model call is triggered by merely reading historical jobs.
