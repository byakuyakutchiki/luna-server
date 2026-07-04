# RAPPORT D'AUDIT GUARDIAN — 2026-07-04

> Aucun déploiement effectué pendant cet audit.  
> Référence production : `luna-beta-00820-ltr`  
> URL principale : `https://luna-beta-gly3g647na-ew.a.run.app/`

---

## 1. Résumé exécutif

- ✅ Repo synchronisé avec la production stable `00820-ltr`.
- ✅ `static/guardian.html` et autres fichiers graphiques restaurés.
- ⚠️ Anomalie "3 contacts alertés" reproduite et expliquée : comptage SMS + DM Luna.
- ⚠️ APK actuelle (v3.1) n'a pas de service natif Vosk : elle utilisera Web Speech API du WebView.
- ✅ `/api/guardian/sos` fonctionne avec session active : SMS + appel réels passés.
- ❌ `event.description` dans `guardian_sos` ne conserve pas le contexte vocal dans l'événement (seul le SMS/appel l'utilise).
- ✅ Adresse textuelle ajoutée dans le SMS via reverse geocoding (patch local non déployé).

---

## 2. État du repo

| Élément | État |
|---------|------|
| Branche | `feature/sprint-a-ux` |
| Checklist poussée | ✅ `docs/GUARDIAN_CHECKLIST.md` |
| Fichiers `static/` | ✅ Identiques à `00820-ltr` |
| `luna_web.py` | ✅ Identique à `00820-ltr` |
| `core/guardian/` | ✅ Identique à `00820-ltr` |
| `deploy.sh` | ✅ Modifié localement (Twilio, PV_SIGNED, etc.) |
| `android-app/` | ✅ Modifié localement (version lue du manifeste, URL principale) |
| APK | ✅ v3.1 (versionCode 22), signée, pointe vers URL principale `/guardian` |

---

## 3. Anomalie "3 contacts alertés"

### 3.1 Reproduction

Session `guard_36d0d0c457`, tenant 1.

**Contact de confiance en base :**
```json
{
  "name": "Ludovic",
  "phone": "+33658477952",
  "relation": "famille"
}
```

**Réponse `/api/guardian/sos` :**
```json
{
  "success": true,
  "alerts_sent_to": 3,
  "calls_placed": 1,
  "message": "SOS envoyé à 3 contact(s)"
}
```

### 3.2 Explication

Dans `luna_web.py:15488-15638` (`guardian_sos`) :

```python
total_sent = len(sms_results.get("sent", [])) + len(dm_results.get("sent", []))
```

- 1 SMS envoyé à Ludovic
- 2 DM Luna envoyés à des amis/trusted friends
- **Total affiché = 3**

### 3.3 Ce n'est pas une limite d'abonnement

- Limite max contacts : 5 (`core/memory/redis_client.py:321`)
- Offre Essentiel mentionne "3 contacts" mais ce n'est pas une limite technique ici
- Le chiffre 3 vient bien du comptage SMS + DM

### 3.4 Frontend

Dans `static/guardian.html:1514` et `1830` :

```javascript
showAlertOnMap('🆘 SOS activé — '+(d.alerts_sent_to||0)+' contact(s) alerté(s)', ...)
```

Le frontend affiche fidèlement ce que le backend renvoie.

### 3.5 Recommandation

Séparer les compteurs ou changer le wording :
- Option A : `alerts_sent_to` ne compte que les SMS/appels (contacts de confiance)
- Option B : ajouter `dm_sent_to` et afficher "1 contact par SMS + 2 amis par message Luna"
- Option C : changer le message utilisateur en "3 personnes alertées" au lieu de "3 contacts"

---

## 4. Audit du flux vocal

### 4.1 Architecture réelle dans `00820-ltr`

```
APK / navigateur
↓
window.lunaEmergencyVoiceDetected(text, confidence, context)
  dans static/guardian.html:1762
↓
openVocalCountdown()
↓
_triggerSOSVocal()
  dans static/guardian.html:1808
↓
POST /api/guardian/sos/{session_id}
  body: { incident_id, source:'vocal', context, transcript }
↓
luna_web.py:15488 guardian_sos()
↓
SMS (build_sms_alert_v1 avec circumstances=context)
DM Luna
Appel vocal (_call_msg inclut alert_desc avec context)
```

### 4.2 Texte brut transmis

- `text` : texte reconnu (ex: "Au secours, il est devant la porte")
- `context` : enrichi par `/api/guardian/voice-context` ou passé directement
- `transcript` : phrase brute complète

### 4.3 `last_words` / équivalent

Pas de champ `last_words` dans ce flux.  
L'équivalent est `context` (résumé LLM) + `transcript` (brut).

### 4.4 Phrase complète après "au secours"

✅ Oui, elle est envoyée.

- `_voiceTranscript` stocke la phrase complète
- `_enrichVoiceContext()` envoie le transcript à `/api/guardian/voice-context` pour obtenir un résumé
- Le résumé est passé dans `context` au backend
- Le backend l'utilise dans le SMS et l'appel

### 4.5 Backend reçoit-il seulement le mot-clé ou tout le contexte ?

✅ Le backend reçoit tout le contexte.

Dans `guardian_sos` :
```python
ctx_summary = (body.get("context") or "").strip()
alert_desc = (base_desc + " — " + ctx_summary) if ctx_summary else base_desc
sms_body = build_sms_alert_v1(person_name, lat, lng, circumstances=ctx_summary)
_call_msg = f"Alerte Guardian pour {person_name}. {alert_desc}.{_pos_txt} ..."
```

### 4.6 Point faible détecté

L'événement `sos_triggered` créé par `engine.trigger_sos()` a une description fixe :

```python
description="🆘 Bouton SOS activé par l'utilisateur"
```

Il ne contient **pas** le contexte vocal. Seuls le SMS et l'appel vocal le contiennent.

### 4.7 APK actuelle (v3.1)

L'APK buildée actuellement :
- n'a **pas** de service natif Vosk
- n'a **pas** de `GuardianService`
- n'expose **pas** `LunaBridge.setGuardianProtection`
- utilisera donc la **Web Speech API du WebView** pour la reconnaissance vocale

Cela peut poser problème car :
- Web Speech API dans WebView Android n'est pas toujours disponible/silencieuse
- Elle peut jouer des tonalités (bip)
- Elle peut s'arrêter en arrière-plan

### 4.8 Logs Cloud Run à surveiller

Commande :
```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="luna-beta" AND ("GUARDIAN_SR" OR "guardian_sos" OR "Guardian alert SMS" OR "Guardian DM alert" OR "SOS call" OR "[EMERGENCY CALL]")' \
  --project=crypto-parser-475411-k4 \
  --freshness=30m \
  --limit=150
```

Logs observés lors du test :
```
INFO:luna.guardian.alerts:Guardian alert SMS sent to Ludovic (+33658477952)
INFO:luna.guardian.alerts:Guardian DM alerts: 2 sent, 0 failed
WARNING:integrations.twilio.voice_client:[EMERGENCY CALL] lancé sid=... -> +33658477952 status=queued
```

---

## 5. Test `/api/guardian/sos` avec session active

### 5.1 Création session

```bash
POST /api/guardian/start
Authorization: Bearer <token>
Body: {"profile_type":"senior"}
```

Réponse :
```json
{
  "success": true,
  "session_id": "guard_36d0d0c457",
  "config": {
    "emergency_contacts": [
      {"name": "Ludovic", "phone": "+33658477952", "relation": "famille"}
    ]
  }
}
```

### 5.2 Déclenchement SOS vocal

```bash
POST /api/guardian/sos/guard_36d0d0c457
Authorization: Bearer <token>
Body: {
  "incident_id": "test-audit-001",
  "source": "vocal",
  "context": "Au secours, il est devant la porte et essaie d'entrer",
  "transcript": "Au secours, il est devant la porte et essaie d'entrer"
}
```

Réponse :
```json
{
  "success": true,
  "alerts_sent_to": 3,
  "calls_placed": 1,
  "guardian_sms_enabled": true,
  "sms_blocked": 0,
  "message": "SOS envoyé à 3 contact(s)"
}
```

### 5.3 Résultat

- ✅ SMS reçu par +33658477952
- ✅ Appel Twilio lancé vers +33658477952
- ⚠️ Message "3 contact(s)" alors qu'1 seul contact de confiance

---

## 6. Préparation test téléphone APK

### 6.1 APK disponible

- Fichier : `static/luna-proprio.apk`
- Version : 3.1 (versionCode 22)
- URL : `https://luna-beta-674304336025.europe-west1.run.app/download/luna.apk`
- Pointe vers : `https://luna-beta-674304336025.europe-west1.run.app/guardian`

### 6.2 Avant le test

1. Désinstaller l'ancienne APK.
2. Télécharger la nouvelle.
3. Installer.
4. Se connecter avec le compte.
5. Démarrer une session Guardian.

### 6.3 Test à réaliser

1. Ouvrir Guardian.
2. Autoriser le micro.
3. Démarrer la protection.
4. Dire clairement : **"Au secours, il est devant la porte et essaie d'entrer"**.
5. Attendre le countdown (5 secondes).
6. Vérifier : panel SOS, SMS, appel.

### 6.4 Attention

L'APK actuelle n'a pas de Vosk natif. Si Web Speech API ne fonctionne pas dans WebView :
- pas de détection vocale
- pas d'alerte

Dans ce cas, il faudra ajouter un service natif Vosk dans l'APK (travail non trivial).

---

## 7. Recommandations avant patch

| Priorité | Action | Impact |
|----------|--------|--------|
| Haute | Corriger l'affichage "3 contacts alertés" | UX |
| Haute | Ajouter le contexte vocal dans l'événement `sos_triggered` | Traçabilité |
| Moyenne | Vérifier si Web Speech API fonctionne dans WebView APK | Fonctionnel |
| Moyenne | Si Web Speech API défaillante, planifier ajout service Vosk natif | Fonctionnel |
| Basse | Réintroduire `/api/app/version` pour anti-drift APK/Cloud Run | Maintenabilité |

---

## 8. Patch local appliqué (non déployé)

### 8.1 Adresse précise dans le SMS

**Fichiers modifiés :**
- `core/guardian/alerts.py` : `build_sms_alert_v1` fait maintenant du reverse geocoding et ajoute l'adresse textuelle.
- `luna_web.py` : passage de `_redis_client` à `build_sms_alert_v1`.

**Résultat du SMS généré :**

```
⚠️ Luna Guardian
Ludovic a demandé de l'aide.
Circonstances : Au secours, il est devant la porte et essaie d'entrer

📍 Localisation :
Rue de l'Oasis, 1, Puteaux
https://maps.google.com/?q=48.8853123,2.2428719

Ouvrez Luna pour plus d'infos.
```

**Impact :** les contacts de confiance ont maintenant l'adresse humaine + le lien Maps précis pour alerter les secours.

---

## 9. Prochaines étapes proposées

1. **Ne pas déployer** avant correction de l'anomalie contacts.
2. Corriger `guardian_sos` pour séparer `sms_sent_to` / `dm_sent_to` ou changer le wording.
3. Tester le wording corrigé.
4. Tester l'APK sur téléphone réel.
5. Selon résultat : ajouter Vosk natif ou non.
6. Déployer une nouvelle révision uniquement après validation complète.

---

*Rapport généré le 2026-07-04. Aucun déploiement effectué.*
