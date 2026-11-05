# Publish AEGIS on GitHub

The repository is pre-cleaned for public viewing, but **review every file before publishing**, especially screenshots and test fixtures. Do not add backups, real master passphrases, authenticator codes, personal vaults, or recordings that may reveal secrets.

## Recommended: GitHub Desktop (Windows)

1. Download and install [GitHub Desktop](https://desktop.github.com/). Sign in to your GitHub account.
2. Extract the provided `AEGIS_GitHub_Ready_Source.zip` to a convenient folder.
3. In GitHub Desktop, choose **File > Add local repository**. Select the extracted `aegis-password-generator` folder (the one containing this README and `desktop` / `web`).
4. If it says the folder is not yet a Git repository, choose **Create a repository here**.
5. Review the changed files. Make an initial commit if prompted, for example: `Initial AEGIS source and documentation`.
6. Select **Publish repository**. Choose `aegis-password-generator`, provide a short description and **uncheck** `Keep this code private` if you're ready to publish publicly.
7. Confirm and open **View on GitHub**. Check that the root README and `desktop` / `web` folders appear.

## Browser upload alternative

1. Visit https://github.com/new and create a **public** repository named `aegis-password-generator` (leave GitHub's optional README, .gitignore and licence creation unchecked because this package already includes those files).
2. In the new empty repository, select **uploading an existing file** or **Add file > Upload files**.
3. Open the extracted `aegis-password-generator` folder. Drag its **contents**, including `desktop`, `web`, `screenshots`, `README.md`, `SECURITY.md` and the `.gitignore`, into the upload area. Verify the folder layout before committing.
4. Select **Commit changes**. Then view the repository's front page and confirm the README appears.

GitHub's browser uploader has a 25 MiB **per file** limit. This source package is deliberately small enough to upload as individual files. Do not upload the compressed ZIP as the only repository file; that hides source browsing and README rendering.

## Optional: offer your Windows installer as a GitHub Release

1. You already have `AEGIS-Setup-0.3.9-Windows-x64.exe` in your **original** `AEGIS_v0.3.9/installer-output` folder. It is not inside this source package.
2. In your GitHub repository, open **Releases > Draft a new release**.
3. Create a tag such as `v0.3.9-desktop` and add the setup EXE as a **release asset**, not as a Git-tracked repository file.
4. If sharing the build before a security review, mark it **Pre-release**, and state that it is unsigned and not independently audited. Check its hash against the existing `.sha256` file first.

GitHub Releases support attaching compiled binaries separately from source code. Be cautious with public distribution of security-sensitive software.

## Ownership and visibility

AEGIS is intentionally **proprietary**, even though this repository is public for portfolio viewing. Do not add MIT, Apache-2.0 or another open-source licence unless that decision changes. The root README describes the reserved rights for original project material; third-party components retain their own terms.

Note that GitHub allows people to view and fork public repositories. If you want to prevent public access to the source entirely, make this repository private and create a separate public showcase containing only screenshots and descriptions.
