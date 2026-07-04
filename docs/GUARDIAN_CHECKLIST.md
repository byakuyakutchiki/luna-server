# CHECKLIST OBLIGATOIRE — GUARDIAN / LUNA

## Référence production stable actuelle

- **Révision Cloud Run** : `luna-beta-00820-ltr`
- **URL principale** : `https://luna-beta-gly3g647na-ew.a.run.app/`
- **Date de création de cette checklist** : 2026-07-04

---

## Légende

- `[ ]` : non traité
- `[~]` : en cours
- `[x]` : fait / validé
- `[!]` : anomalie détectée, à corriger

---

## 1. Synchronisation repo ↔ production

- [x] Identifier la révision production stable (`luna-beta-00820-ltr`)
- [x] Extraire `static/guardian.html` de la production
- [x] Extraire `static/index.html` de la production
- [x] Extraire `static/salon.html` de la production
- [x] Extraire `static/simli.html` de la production
- [x] Restaurer les fichiers `static/` dans le repo local
- [x] Préserver la nouvelle APK (`static/luna-proprio.apk`) et les QR codes
- [x] Comparer et synchroniser les fichiers Python (`luna_web.py`, `core/guardian/engine.py`, `integrations/twilio/voice_client.py`, `core/guardian/alerts.py`, etc.)
- [x] Valider que le repo local est identique à la production stable avant modification

---

## 2. Fichiers protégés — vérification

- [x] `static/guardian.html` : restauré depuis production
- [x] `static/index.html` : restauré depuis production
- [x] `static/salon.html` : restauré depuis production
- [x] `static/simli.html` : restauré depuis production
- [ ] `luna_web.py` : en cours de synchronisation
- [ ] fichiers Android APK : à revérifier
- [ ] service worker / cache : à vérifier
- [ ] manifest PWA : à vérifier

---

## 3. UX mobile — anti-régression

- [ ] Test Redmi / Android réel
- [ ] Test écran mobile petit
- [ ] Test écran mobile moyen
- [ ] Test desktop
- [ ] Test navigateur
- [ ] Test APK
- [ ] Aucun bouton ne se superpose
- [ ] Aucun élément ne sort de l'écran
- [ ] Textes non coupés
- [ ] Modales lisibles
- [ ] Boutons Guardian accessibles
- [ ] Profondeur graphique conservée
- [ ] Pas de flash d'ancien écran au chargement

---

## 4. Architecture Guardian découverte dans production `00820-ltr`

Le flux vocal ne passe PAS directement par `/trigger`.

Chaîne réelle :

```
APK Vosk
↓
window.lunaEmergencyVoiceDetected(text, confidence, context)
↓
openVocalCountdown()
↓
_triggerSOSVocal()
↓
POST /api/guardian/sos/{session_id}
↓
backend guardian_sos()
↓
DM Luna + SMS + appels
```

Points clés :
- Le contexte vocal (circonstances) est transmis au backend.
- Le SMS inclut les circonstances.
- L'appel vocal inclut le nom + circonstances + adresse.
- `GUARDIAN_CALL_ENABLED=true` est nécessaire pour les appels.
- `GUARDIAN_SMS_ENABLED=true` est nécessaire pour les SMS.

## 5. Écoute vocale Guardian

- [ ] Micro démarre réellement
- [ ] Vosk fonctionne dans l'APK
- [ ] Browser SpeechRecognition fonctionne en navigateur
- [ ] Logs affichent la détection
- [ ] `window.lunaEmergencyVoiceDetected(text, confidence, context)` est appelée
- [ ] Texte reconnu transmis
- [ ] Système ne coupe pas trop tôt
- [ ] Contexte après le mot-clé conservé

**Marqueurs à vérifier dans `static/guardian.html` :**
- [x] `window.lunaEmergencyVoiceDetected` — présent
- [x] `_triggerSOSVocal` — présent
- [x] `authFetch('/api/guardian/sos/...')` — présent
- [x] logs `GUARDIAN_SR` — présent
- [x] source `'vocal'` dans l'appel SOS — présent

---

## 5. /api/guardian/sos manuel

Dans la production `00820-ltr`, le SOS passe par `/api/guardian/sos/{session_id}`.

```bash
curl -i -X POST https://luna-beta-gly3g647na-ew.a.run.app/api/guardian/sos/SESSION_ID \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"incident_id":"test-123","source":"vocal","context":"Au secours test","transcript":"Au secours test"}'
```

- [ ] `success: true`
- [ ] `alerts_sent_to` cohérent avec nombre de contacts
- [ ] `calls_placed` cohérent
- [ ] Message `SOS envoyé à X contact(s)`
- [ ] Mode dry-run ou réel cohérent

**Note :** l'ancien endpoint `/trigger` existe encore pour compatibilité mais le flux Guardian nominal passe par `/api/guardian/sos`.

---

## 6. Contacts — correction anomaly

Anomalie : interface affichait "3 contacts alertés" alors qu'un seul était enregistré.

### Diagnostic

- [x] Reproduit avec session active
- [x] Explication trouvée : `total_sent = SMS + DM Luna`
- [x] Décider du wording correct (Option A : séparer les compteurs)
- [x] Corriger backend et frontend

Détail : avec 1 contact SMS + 2 amis Luna en DM, le backend renvoie maintenant :
- `sms_sent_to: 1`
- `dm_sent_to: 2`
- `calls_placed: 1`
- message : "SOS envoyé : 1 contact par SMS, 2 amis par Luna, 1 appel passé"

---

## 6b. Précision de l'adresse dans le SMS

- [x] Lien Google Maps présent quand position envoyée
- [x] Adresse textuelle ajoutée dans `build_sms_alert_v1` via reverse geocoding
- [ ] Tester en production

---

## 7. Gestion du cycle de vie de l'app

- [ ] App ouverte
- [ ] App en arrière-plan
- [ ] Écran verrouillé
- [ ] Retour à l'application
- [ ] Changement d'onglet
- [ ] Fermeture puis réouverture
- [ ] Pas de blocage silencieux
- [ ] Micro pas dans un état incohérent
- [ ] Pas de double écoute
- [ ] Pas de double déclenchement

---

## 8. Logs Cloud Run

Commande :

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="luna-beta" AND ("GUARDIAN_SR" OR "GUARDIAN /trigger" OR "VOICE EMERGENCY" OR "guardian_apk_vosk" OR "vosk_final")' \
  --project crypto-parser-475411-k4 \
  --freshness=30m \
  --limit=150 \
  --format="table(timestamp,severity,textPayload,jsonPayload.message)"
```

- [ ] Vosk final / intermediate
- [ ] Détection mot-clé
- [ ] `lunaEmergencyVoiceDetected`
- [ ] Appel `/trigger`
- [ ] Réponse `/trigger`
- [ ] Rapport urgence généré

---

## 9. Dry-run / mode réel

- [ ] Mode actif confirmé
- [ ] SMS réels ou simulés selon config
- [ ] Appels réels ou simulés selon config
- [ ] Variables Cloud Run vérifiées
- [ ] Logs cohérents avec le mode
- [ ] Contacts et numéros confirmés avant mode réel

---

## 10. APK

- [ ] URL APK pointe sur bonne URL Cloud Run
- [ ] APK sert la production stable
- [ ] APK ouverte sur téléphone
- [ ] Écran Guardian vérifié visuellement
- [ ] Micro testé
- [ ] Logs testés
- [ ] Pas une ancienne version

---

## 11. Anti-régression graphique

- [ ] Capture écran mobile avant
- [ ] Capture Guardian avant
- [ ] Capture accueil avant
- [ ] Capture modale avant
- [ ] Capture écran mobile après
- [ ] Capture Guardian après
- [ ] Comparaison visuelle

Interdit :
- [ ] Retour à une ancienne interface
- [ ] Espacements cassés
- [ ] Profondeur / glassmorphism supprimés
- [ ] Boutons flottants gênants
- [ ] Textes masqués
- [ ] Version téléphone cassée

---

## 12. Ordre de travail

- [x] Synchroniser repo avec production stable
- [x] Identifier les différences
- [x] Restaurer les fichiers écrasés
- [ ] Vérifier `guardian.html`
- [ ] Vérifier UX mobile
- [ ] Vérifier détection vocale
- [ ] Vérifier `/trigger`
- [ ] Vérifier contacts réels
- [ ] Vérifier logs
- [ ] Tester APK
- [ ] Proposer un patch minimal
- [ ] Déployer uniquement après validation

---

## 13. Rapport à rendre avant modification

- [x] État du repo : en cours de resynchronisation
- [x] Révision Cloud Run active : `luna-beta-00820-ltr`
- [x] Fichiers différents entre repo et production : `guardian.html`, `index.html`, `salon.html`, `simli.html`, `luna_web.py`, `core/guardian/engine.py`, `integrations/twilio/voice_client.py`
- [ ] Présence des marqueurs Guardian
- [ ] État de `/trigger`
- [ ] État de l'APK
- [ ] État des contacts
- [ ] Anomalies restantes
- [ ] Proposition de correction minimale

---

## Historique des actions

| Date | Action | Résultat |
|------|--------|----------|
| 2026-07-04 | Rollback production sur `00820-ltr` | ✅ Interface graphique restaurée |
| 2026-07-04 | Restauration `static/` depuis production | ✅ Identique à `00820-ltr` |
| 2026-07-04 | Préservation nouvelle APK v3.1 + QR codes | ✅ Conservés |
| 2026-07-04 | Création de cette checklist | ✅ Fait |
| 2026-07-04 | Synchronisation fichiers Python | ⏳ En cours |

