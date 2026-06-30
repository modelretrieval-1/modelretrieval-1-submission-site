# GitHub Secrets

## Purpose

This document defines the GitHub Actions secrets required by `.github/workflows/ci-cd.yml`.

Secrets may be configured as repository secrets or environment-specific secrets. Environment-specific secrets are recommended for `staging` and `production`.

## Required Staging Secrets

| Secret | Example | Description |
|---|---|---|
| `STAGING_HOST` | `203.0.113.10` | Sakura VPS hostname or IP. |
| `STAGING_USER` | `deploy` | SSH user for staging deployment. |
| `STAGING_SSH_KEY` | private key text | Private SSH key matching the VPS deploy user's authorized key. |
| `STAGING_PATH` | `/opt/modelretrieval/staging` | Directory containing staging `compose.yml` and `.env`. |
| `STAGING_URL` | `https://submission-staging.modelretrieval-1.happysocial.net` | Public staging URL used by smoke checks. |

## Required Production Secrets

| Secret | Example | Description |
|---|---|---|
| `PRODUCTION_HOST` | `203.0.113.10` | Sakura VPS hostname or IP. |
| `PRODUCTION_USER` | `deploy` | SSH user for production deployment. |
| `PRODUCTION_SSH_KEY` | private key text | Private SSH key matching the VPS deploy user's authorized key. |
| `PRODUCTION_PATH` | `/opt/modelretrieval/production` | Directory containing production `compose.yml`, `.env`, and `backup.sh`. |
| `PRODUCTION_URL` | `https://submission.modelretrieval-1.happysocial.net` | Public production URL used by smoke checks. |

## Built-In GitHub Token

The workflow uses `GITHUB_TOKEN` to push images to GitHub Container Registry.

Required workflow permissions:

```yaml
permissions:
  contents: read
  packages: write
```

The workflow already declares these permissions.

## SSH Key Guidance

The VPS `deploy` user should be created without a password and should authenticate by SSH key only.

Recommended user creation command:

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy
```

Create a deploy key for GitHub Actions:

```bash
ssh-keygen -t ed25519 -C "modelretrieval-deploy" -f modelretrieval-deploy
```

Install the public key on the VPS deploy user:

```bash
cat modelretrieval-deploy.pub
```

Append that public key to:

```text
/home/deploy/.ssh/authorized_keys
```

Store the private key contents in GitHub:

```text
STAGING_SSH_KEY
PRODUCTION_SSH_KEY
```

You may use one key for both environments on the same VPS, or separate keys for stricter separation.

Do not store a VPS user password in GitHub. The workflow is designed for SSH key authentication only.

## Remote Path Requirements

The workflow assumes these files exist on the VPS:

Staging:

```text
/opt/modelretrieval/staging/compose.yml
/opt/modelretrieval/staging/.env
/opt/modelretrieval/staging/data/
```

Production:

```text
/opt/modelretrieval/production/compose.yml
/opt/modelretrieval/production/.env
/opt/modelretrieval/production/data/
/opt/modelretrieval/production/backup.sh
```

The production deploy job runs:

```bash
cd "$PRODUCTION_PATH"
ENVIRONMENT=production ./backup.sh
```

So `backup.sh` must be executable on the VPS.

## Image Variables

The workflow updates `APP_IMAGE` in the remote `.env` file during deployment.

Staging receives the image built from the branch push:

```text
ghcr.io/<owner>/<repo>:main-<short-sha>
```

Production receives the image built from the version tag:

```text
ghcr.io/<owner>/<repo>:vYYYY.MM.DD
```

Before CI/CD has run, set `APP_IMAGE` manually in the VPS `.env` file.

For staging:

```text
APP_IMAGE=ghcr.io/<owner>/<repo>:latest-staging
```

For production:

```text
APP_IMAGE=ghcr.io/<owner>/<repo>:vYYYY.MM.DD
```

Check the current value:

```bash
grep APP_IMAGE /opt/modelretrieval/staging/.env
grep APP_IMAGE /opt/modelretrieval/production/.env
```

The image can be found in:

```text
GitHub repository -> Packages
```

If `docker compose pull` returns `unauthorized`, log in to GHCR on the VPS as the Docker Compose user:

```bash
su - deploy
echo "<github_pat>" | docker login ghcr.io -u "<github_username>" --password-stdin
```

The token needs `read:packages`. Private repositories or packages may also require `repo`.

## Environment Protection

Recommended GitHub environment rules:

- `staging`: no manual approval required.
- `production`: require manual approval before deployment.

This preserves automatic staging deployment while keeping production deliberate.

## Secret Checklist

- [ ] `STAGING_HOST`
- [ ] `STAGING_USER`
- [ ] `STAGING_SSH_KEY`
- [ ] `STAGING_PATH`
- [ ] `STAGING_URL`
- [ ] `PRODUCTION_HOST`
- [ ] `PRODUCTION_USER`
- [ ] `PRODUCTION_SSH_KEY`
- [ ] `PRODUCTION_PATH`
- [ ] `PRODUCTION_URL`
- [ ] GitHub package permissions allow GHCR writes.
- [ ] Production environment requires approval.
