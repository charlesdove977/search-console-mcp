# Setup walkthrough

Most users only need the install + auth steps in the main [README](../README.md). This file covers two extra situations.

---

## "This app is blocked" during `gcloud auth application-default login`

As of 2026, Google's default gcloud OAuth client can no longer request "sensitive" scopes including `analytics.edit` and (sometimes) `webmasters.readonly`. If you hit a "this app is blocked" page mid-auth, you need a custom OAuth client owned by your own GCP project.

### Steps

1. Open [console.cloud.google.com](https://console.cloud.google.com/), pick a project.

2. Go to the new **Google Auth Platform** UI:
   ```
   https://console.cloud.google.com/auth/clients?project=YOUR_PROJECT
   ```

3. Click **Create client** → choose **Desktop app** → name it (`mcp-adc-client` works) → Create.

4. Click into the new client and **Download JSON**. Save it locally with restrictive permissions:
   ```bash
   mv ~/Downloads/client_secret_<long-name>.json ~/.config/mcp-adc-client.json
   chmod 600 ~/.config/mcp-adc-client.json
   ```

5. Add the scopes you need to the consent screen at:
   ```
   https://console.cloud.google.com/auth/scopes?project=YOUR_PROJECT
   ```
   Click **Add or remove scopes**, paste these into the "Manually add scopes" box (one per line), then click **Add to table** and **Update**:
   ```
   https://www.googleapis.com/auth/webmasters.readonly
   https://www.googleapis.com/auth/analytics.readonly
   ```
   Add any other analytics scopes you want (`analytics`, `analytics.edit`, etc.) if you also plan to use Google's `analytics-mcp` alongside this one.

6. Rerun ADC login with `--client-id-file`:
   ```bash
   gcloud auth application-default login \
     --client-id-file=$HOME/.config/mcp-adc-client.json \
     --scopes=openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/webmasters.readonly
   ```

The custom client owns the consent flow, so Google permits the scopes that the default shared client cannot.

---

## Verifying which scopes your token has

If a tool returns `403 insufficient authentication scopes`, check what's actually on your token:

```bash
TOKEN=$(gcloud auth application-default print-access-token)
curl -s "https://oauth2.googleapis.com/tokeninfo?access_token=$TOKEN" \
  | python3 -m json.tool
```

The `scope` field lists every scope your current ADC token holds. If `webmasters.readonly` is missing, rerun the gcloud command with it explicitly in the `--scopes` flag.

---

## Org-policy blocking service account keys

Some Google Cloud organizations enforce the `iam.disableServiceAccountKeyCreation` policy (and its newer "managed" version, `iam.managed.disableServiceAccountKeyCreation`). This is great security hygiene but blocks the "service account JSON key" path entirely.

If you want service account auth despite this policy, you need `roles/orgpolicy.policyAdmin` at the org level, then override **both** versions of the constraint at the project level (Override parent's policy → set to "Not enforced"). Most users should just stick with ADC instead — it works around the policy entirely.
