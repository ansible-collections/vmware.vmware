# SonarCloud

This collection uses [SonarCloud](https://sonarcloud.io/) (SonarQube Cloud) for static analysis, security hotspots, and code coverage reporting.

Project: [ansible-collections_vmware.vmware](https://sonarcloud.io/project/overview?id=ansible-collections_vmware.vmware)

## Configuration

- **`sonar-project.properties`** at the repository root defines project keys, source paths, and coverage report location.
- **`.github/workflows/ansible-unit.yml`** — unit matrix; one cell uploads artifact **`coverage`** (no Sonar token in this workflow).
- **`.github/workflows/sonarcloud.yml`** — fork-safe **`workflow_run`** follow-up ([amazon.aws](https://github.com/ansible-collections/amazon.aws/blob/main/.github/workflows/sonarcloud.yml) pattern).

Flow:

1. **Units** (`pull_request` / `push`) — matrix runs tests; Python 3.12 / ansible-core 2.20 cell uploads `coverage.xml`.
2. **unit-check** — branch-protection gate; all matrix jobs must pass.
3. **SonarCloud** — triggered when **Units** completes successfully; downloads coverage from that run, checks out `workflow_run.head_sha`, runs SonarScanner with the org secret.

## Org secret

CI uses the **ansible-collections** organization secret:

`ANSIBLE_COLLECTIONS_ORG_SONAR_TOKEN_CICD_BOT`

Only the **SonarCloud** workflow (`workflow_run`) uses this secret. The **Units** workflow never receives it. Do not commit tokens to the repository.

## Fork pull requests

External fork PRs do not expose org secrets to the **Units** workflow. After units pass, **SonarCloud** runs from the default-branch workflow definition (trusted context) with the org token, downloads the coverage artifact from the **Units** run, and analyzes `workflow_run.head_sha`.

**Note:** `workflow_run` Sonar wiring must exist on the repository default branch before fork PRs get Sonar results. CI on a personal fork alone still requires a repo-level `SONAR_TOKEN` if you want Sonar there.

## Coverage

SonarCloud expects **`coverage.xml`** (see `sonar.python.coverage.reportPaths` in `sonar-project.properties`). CI generates it from **unit tests only** via `ansible-test` coverage on the primary matrix cell. Paths in the XML are rewritten to be repo-relative so Sonar resolves sources correctly.

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
- [amazon.aws Sonar + coverage (PR #2871)](https://github.com/ansible-collections/amazon.aws/pull/2871)
