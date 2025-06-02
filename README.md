# GitHub Contribution Graph Art Generator

A simple Python tool to draw images, text, or templates on your GitHub contribution graph by making custom-dated commits.

Maintained by **Ma-s-on** — I'll keep it up as long as I feel like it, and it'll work until it doesn't.

## Features
- Draw images, text, or use templates on your GitHub contribution graph
- Interactive wizard for easy use
- Secure GitHub authentication (PAT stored with keyring)
- SSH and HTTPS push support
- Import/export templates (JSON)
- Dry run/test mode
- Terminal and pop-up image preview
- Error logging

## Install
1. Python 3.8+
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. (Optional) For best text rendering, put a monospace font (like `DejaVuSansMono.ttf`) in the script folder.
## Usage
**Wizard mode (recommended):**
```sh
python github_contribution_generator.py
```

**Command-line mode:**
```sh
python github_contribution_generator.py --help
```

## Auth
- Use the wizard to connect your GitHub account and store your PAT securely.
- [Create a PAT here](https://github.com/settings/tokens) (scopes: `repo` or `public_repo`).
- SSH works if you have it set up.

## Templates
- Use built-in templates, or import/export your own as JSON.
- Community template sharing coming soon.

## Troubleshooting
- Missing dependencies? Run: `pip install -r requirements.txt`
- No font? Put `DejaVuSansMono.ttf` or `Courier.ttf` in the script folder.
- Git errors? Make sure Git is installed and configured.
- Auth issues? Double-check your PAT and scopes, or reconnect via the wizard.
- Other errors? See `github_contribution_generator.log`.

## Platform
- Works on Windows, Mac, and Linux. Terminal colors and fonts may look different.

## License
MIT
---
![ineedajob](https://github.com/user-attachments/assets/e35f19b5-d597-4af2-bdb0-14ce50109d36)
---

If you like it, use it. If you break it, you get to keep both pieces. Enjoy
