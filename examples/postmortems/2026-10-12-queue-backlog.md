# Postmortem: order queue backlog on 2026-10-12

## Summary

Order confirmation emails were delayed by up to 55 minutes because the worker
pool consuming the `orders` queue stopped scaling up.

## Impact

About 12,400 confirmation emails were delayed. No orders were lost.

## Timeline (UTC)

| Time | Event |
| --- | --- |
| 09:10 | Autoscaler loses access to the queue-depth metric after a credentials rotation |
| 09:26 | Queue-depth alert fires and pages the on-call engineer (detection) |
| 09:29 | On-call acknowledges the page and starts investigating |
| 09:48 | Workers scaled up manually; backlog starts draining (mitigated) |
| 10:21 | Backlog cleared, incident resolved |

## Root cause

The credentials rotation job updated the secret but the autoscaler only reads
it at start-up, so it kept using the old credentials and saw no metric data.
With no data it held the worker count at its minimum.

## Lessons learned

- The queue-depth alert worked, but 16 minutes after the trigger is too slow.
- The rotation runbook did not list the autoscaler as a consumer of the secret.

## Action items

| Action | Owner | Due |
| --- | --- | --- |
| Make the autoscaler reload credentials without a restart | @priya | 2026-10-30 |
| Alert when the autoscaler has received no metric data for 5 minutes | @marcus | 2026-10-23 |
| Add the autoscaler to the secret-consumers list in the rotation runbook | @priya | 2026-10-16 |
