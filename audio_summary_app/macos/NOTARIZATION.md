API‑key Notarization (Recommended)

What you need from App Store Connect:
- Issuer ID (UUID)
- Key ID (10 chars)
- Private key file (.p8) for that Key ID

Store credentials once on this machine:
1) Place the .p8 at a safe path (example: ~/.appstoreconnect/AuthKey_XXXXXXX.p8)
2) Run:

   xcrun notarytool store-credentials audio-summary-notary-api \
     --issuer ISSUER_ID \
     --key-id KEY_ID \
     --key /path/to/AuthKey_KEYID.p8

Build, notarize, staple:

   export DEVELOPER_ID="Developer ID Application: Your Name (TEAMID)"
   export NOTARY_PROFILE="audio-summary-notary-api"
   cd audio_summary_app && bash build_pyinstaller.sh

After acceptance, the script staples the ticket and re‑zips.

