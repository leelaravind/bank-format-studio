# CI workflow (parked)

The local Git credential lacks the GitHub 'workflow' scope, so pushing .github/workflows/ was rejected.

OWNER ACTION: restore CI with your own credentials:
```git mv ci/github-workflow-ci.yml .github/workflows/ci.yml```  then commit and push.
Every CI step was executed locally (see IMPLEMENTATION-COMPLETION-REPORT.md).
