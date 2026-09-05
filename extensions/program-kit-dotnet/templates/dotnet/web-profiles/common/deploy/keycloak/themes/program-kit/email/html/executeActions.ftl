<#ftl output_format="HTML">
<#assign requiredActionsText><#if requiredActions??><#list requiredActions><#items as requiredAction>${msg("requiredAction.${requiredAction}")}<#sep>, </#sep></#items></#list></#if></#assign>
<!doctype html>
<html lang="en"><body style="margin:0;background:#f4f7fb;color:#172033;font-family:Arial,sans-serif">
<div data-program-kit-email="execute-actions-v1" style="max-width:560px;margin:32px auto;background:#fff;border-radius:16px;padding:36px">
  <p style="font-size:13px;font-weight:700;letter-spacing:.12em;color:#536dfe;text-transform:uppercase">Program Kit</p>
  <h1>Complete your account setup</h1>
  <p style="font-size:16px;line-height:1.6">Your ${realmName} account needs these actions: ${requiredActionsText}.</p>
  <p><a href="${link}" style="display:inline-block;background:#4355db;color:#fff;text-decoration:none;font-weight:700;padding:13px 20px;border-radius:9px">Continue securely</a></p>
  <p style="font-size:13px;color:#62708a">This link expires in ${linkExpirationFormatter(linkExpiration)}.</p>
</div></body></html>
