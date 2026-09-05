<#ftl output_format="plainText">
<#assign requiredActionsText><#if requiredActions??><#list requiredActions><#items as requiredAction>${msg("requiredAction.${requiredAction}")}<#sep>, </#sep></#items></#list></#if></#assign>
PROGRAM KIT | ACCOUNT ACTION REQUIRED

Your ${realmName} account needs these actions: ${requiredActionsText}.

Continue within ${linkExpirationFormatter(linkExpiration)}:
${link}
