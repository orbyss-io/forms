<#ftl output_format="HTML">
<!doctype html>
<html lang="en">
<body style="margin:0;background:#f4f7fb;color:#172033;font-family:Arial,sans-serif">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f7fb;padding:32px 16px">
    <tr><td align="center">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" data-program-kit-email="password-reset-v1" style="max-width:560px;background:#ffffff;border-radius:16px;padding:36px;box-shadow:0 8px 28px rgba(28,45,74,.10)">
        <tr><td style="font-size:13px;font-weight:700;letter-spacing:.12em;color:#536dfe;text-transform:uppercase">Program Kit</td></tr>
        <tr><td><h1 style="font-size:26px;line-height:1.25;margin:14px 0">Reset your password</h1></td></tr>
        <tr><td><p style="font-size:16px;line-height:1.6;margin:0 0 24px">A password reset was requested for your ${realmName} account. Use the secure button below within ${linkExpirationFormatter(linkExpiration)}.</p></td></tr>
        <tr><td><a href="${link}" style="display:inline-block;background:#4355db;color:#fff;text-decoration:none;font-weight:700;padding:13px 20px;border-radius:9px">Choose a new password</a></td></tr>
        <tr><td><p style="font-size:13px;line-height:1.5;color:#62708a;margin:28px 0 0">If you did not request this, you can ignore this email. The link can be used only for this security action.</p></td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
