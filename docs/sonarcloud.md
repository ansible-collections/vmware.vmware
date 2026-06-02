# SonarCloud

This collection uses [SonarCloud](https://sonarcloud.io/) (SonarQube Cloud) for static analysis, security hotspots, and code coverage reporting.

Project: [ansible-collections_vmware.vmware](https://sonarcloud.io/project/overview?id=ansible-collections_vmware.vmware)

## Configuration

- **`sonar-project.properties`** at the repository root defines project keys, source paths, and coverage report location.
- **`.github/workflows/sonarcloud.yml`** — reusable **`workflow_call`** workflow ([kubernetes.core](https://github.com/ansible-collections/kubernetes.core/blob/main/.github/workflows/sonarcloud.yml) pattern).
- **`.github/workflows/ansible-unit.yml`** — unit matrix; **`ansible-test-gh-action`** emits Cobertura XML (`coverage-report-files`) on the primary cell (Python 3.12 / ansible-core 2.20); uploads artifact **`coverage`** for Sonar; then **`sonarcloud`** caller.

Flow (single **Units** workflow run):

1. **units** (matrix) — `coverage: always` on one cell only; action runs tests and produces XML; that cell uploads `coverage.xml`.
2. **unit-check** — all matrix jobs must pass.
3. **sonarcloud** — calls `sonarcloud.yml`; downloads artifact; runs SonarScanner.

## Org secret

CI uses the **ansible-collections** organization secret:

`ANSIBLE_COLLECTIONS_ORG_SONAR_TOKEN_CICD_BOT`

The caller passes it explicitly (`secrets:` mapping, not `secrets: inherit`). Do not commit tokens to the repository.

## Fork pull requests

The **sonarcloud** job is skipped when `github.event.pull_request.head.repo.full_name != github.repository` (fork PRs). Same-repository PRs and pushes to protected branches run Sonar when the secret is configured. This avoids checking out untrusted fork code in a privileged context (SonarCloud S7631 / `workflow_run` fork risk).

## Coverage

SonarCloud expects **`coverage.xml`** (see `sonar.python.coverage.reportPaths` in `sonar-project.properties`). CI generates it from **unit tests only** via `ansible-test coverage xml`. Paths in the XML are rewritten to be repo-relative so Sonar resolves sources correctly.

## Local validation (optional)

1. Install [SonarScanner CLI](https://docs.sonarqube.org/latest/analyzing-source-code/scanners/sonarscanner/).
2. Create a user token in SonarCloud (**My Account → Security**) and export `SONAR_TOKEN`.
3. Generate coverage locally (see **`make units`**; add `ansible-test coverage xml` and copy XML to `coverage.xml` at repo root).
4. From the repository root:

   ```bash
   sonar-scanner -Dsonar.projectBaseDir=. -Dsonar.host.url=https://sonarcloud.io
   ```

## Related documentation

- [SonarQube Cloud — CI-based analysis](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/ci-based-analysis)
- [Analysis parameters](https://docs.sonarqube.org/latest/analysis/analysis-parameters/)
- [kubernetes.core Sonar onboarding (PR #1124)](https://github.com/ansible-collections/kubernetes.core/pull/1124)
