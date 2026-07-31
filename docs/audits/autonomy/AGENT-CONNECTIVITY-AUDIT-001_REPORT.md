# Rapport d'audit : AGENT-CONNECTIVITY-AUDIT-001

- **Mission ID** : AGENT-CONNECTIVITY-AUDIT-001
- **Date** : 2026-07-17T19:41:10.866670+00:00
- **Runner ID** : luna-vm-01
- **Statut global** : ok
- **Méthode** : audit non destructif sans appel IA

## Résumé

- Kimi CLI disponible
- Cle API DeepSeek configuree
- Cle API OpenAI configuree
- Reseau deepseek accessible
- Reseau openai accessible

## Kimi CLI

- Chemin configuré : `/home/ludo/.kimi-code/bin/kimi`
- Chemin résolu : `/home/ludo/.kimi-code/bin/kimi`
- Disponible : True

## DeepSeek

- Clé API configurée : True
- Suffixe clé : `...7519`
- Modèle : `deepseek-chat`

## OpenAI / Codex

- Clé API configurée : True
- Suffixe clé : `...uwQA`
- Modèle : `gpt-4o-mini`

## Connectivité réseau

- **deepseek** : api.deepseek.com → True (SSL OK (TLSv1.3, TLS_AES_128_GCM_SHA256))
- **openai** : api.openai.com → True (SSL OK (TLSv1.3, TLS_AES_256_GCM_SHA384))
- **deepseek_http** : https://api.deepseek.com/ → True (HTTP 401 (endpoint protege/anti-bot, accessible))
- **openai_http** : https://api.openai.com/ → True (HTTP 421 (endpoint protege/anti-bot, accessible))

## Routing / fallback

- **auditor_fallback** : agent effectif `kimi` (kimi fallback quand deepseek indisponible)
- **coordinator_fallback** : agent effectif `kimi` (kimi fallback quand openai indisponible)

## Conclusion

Tous les agents sont configurés et les endpoints réseau sont accessibles. Le superviseur peut router les missions vers Kimi, DeepSeek ou OpenAI/Codex avec fallback sur Kimi.
