# Postmortem: API outage on 2026-11-01

## Summary

The public API returned 502 errors for about 40 minutes after a config push
removed the health-check path from the load balancer.

## Impact

Roughly 38% of API requests failed. Checkout was unavailable for most customers.

## Timeline

- 14:02 Config change deployed to the edge load balancers
- 14:05 Error rate starts climbing
- 14:31 Customer support escalates after several tickets
- 14:44 Config rolled back, error rate back to normal

## Root cause

This was human error. The on-call engineer should have checked the diff more
carefully and forgot to run the validation script before pushing.

## Action items

- Improve monitoring
- Be more careful with load balancer changes (owner: @dana)
- Add a CI step that runs `lb-validate` on every config pull request. Owner: @sam, due 2026-11-15
- Look into canary deploys for edge config
