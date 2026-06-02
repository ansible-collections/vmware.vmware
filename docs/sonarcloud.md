# SonarCloud

This collection uses [SonarCloud](https://sonarcloud.io/) (SonarQube Cloud) for static analysis, security hotspots, and code coverage reporting.

Project: [ansible-collections_vmware.vmware](https://sonarcloud.io/project/overview?id=ansible-collections_vmware.vmware)

## Configuration

- **`sonar-project.properties`** at the repository root defines project keys, source paths, and coverage report location.
- **`.github/workflows/ansible-unit.yml`** (`name: Units`) — unit matrix, **`coverage`** job (artifact **`coverage`**), **`unit-check`** gate.
- **`.github/workflows/sonarcloud.yml`** ([amazon.aws-style](https://github.com/ansible-collections/amazon.aws/blob/main/.github/workflows/sonarcloud.yml) **`workflow_run`**): triggered when **Units** completes successfully; downloads **`coverage*`** artifacts and runs the SonarScanner.

Flow:

1. **Units** workflow (`ansible-unit.yml`) — units → unit-check → coverage (uploads `coverage.xml`).
2. **SonarCloud** workflow — runs after **Units** succeeds; separate trusted job with org `SONAR_TOKEN`.

`workflow_run` listens for the workflow display name **`Units`**, not the file name `ansible-unit.yml`.

## Org secret

CI uses the **ansible-collections** organization secret:

`ANSIBLE_COLLECTIONS_ORG_SONAR_TOKEN_CICD_BOT`

Workflows reference it as `${{ secrets.ANSIBLE_COLLECTIONS_ORG_SONAR_TOKEN_CICD_BOT }}`. Do not commit tokens to the repository.

## Fork pull requests

Sonar runs in a follow-up workflow after **Units** (`ansible-unit.yml`) completes. Fork PR behavior follows GitHub org secret and `workflow_run` trust rules; fork PRs may not receive Sonar results until changes are merged or workflow runs are approved.

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
