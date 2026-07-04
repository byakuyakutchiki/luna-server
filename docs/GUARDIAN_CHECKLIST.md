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
- [~] Comparer et synchroniser les fichiers Python (`luna_web.py`, `core/guardian/engine.py`, `integrations/twilio/voice_client.py`)
- [ ] Valider que le repo local est identique à la production stable avant modification

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

## 4. Écoute vocale Guardian

- [ ] Micro démarre réellement
- [ ] Vosk fonctionne dans l'APK
- [ ] Browser SpeechRecognition fonctionne en navigateur
- [ ] Logs affichent la détection
- [ ] `window.lunaEmergencyVoiceDetected(text, confidence)` est appelée
- [ ] Texte reconnu transmis
- [ ] Système ne coupe pas trop tôt
- [ ] Contexte après le mot-clé conservé

**Marqueurs à vérifier dans `static/guardian.html` :**
- [ ] `window.lunaEmergencyVoiceDetected`
- [ ] `guardian_apk_vosk`
- [ ] `authFetch('/trigger'`
- [ ] logs `[GUARDIAN_SR]`
- [ ] logs `calling /trigger from sr_emergency`

---

## 5. /trigger manuel

```bash
curl -i -X POST https://luna-beta-gly3g647na-ew.a.run.app/trigger \
  -H "Content-Type: application/json" \
  -d '{"keyword":"au secours test","source":"manual_test","last_words":"au secours test","summary":"au secours test"}'
```

- [ ] `ok: true`
- [ ] `status: triggered`
- [ ] `emergency_report.triggered: true`
- [ ] SMS comptabilisés correctement
- [ ] Appels comptabilisés correctement
- [ ] Mode dry-run ou réel cohérent

---

## 6. Contacts — correction anomaly

Anomalie : interface affichait "3 contacts alertés" alors qu'un seul était enregistré.

- [ ] Afficher le nombre réel de contacts
- [ ] "1 contact alerté" si 1 contact
- [ ] "X contacts alertés" si plusieurs
- [ ] Backend et frontend cohérents
- [ ] SMS envoyés = nombre réel
- [ ] Appels passés = nombre réel
- [ ] Ne pas confondre limite max (3) et nombre réel
- [ ] Vérifier `contacts[:3]`, `sms_count`, `calls_count` dans `luna_web.py`

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

