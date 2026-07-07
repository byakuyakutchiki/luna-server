.md
# Checklist de pré-déploiement — Guardian APK / trace

## Objectif
Éviter les déploiements incomplets où des fichiers de debug, des routes ou des URLs sont oubliés.

## Quand utiliser cette checklist
- Avant chaque déploiement sur `trace---luna-beta-gly3g647na-ew.a.run.app`.
- Avant chaque déploiement sur `phase-a-auth---...`.
- Avant tout déploiement diagnostic lié à Guardian.

---

## Checklist

### 1. Identité du déploiement

- [ ] Branche exacte : ________________________________
- [ ] Commit exact (hash) : ___________________________
- [ ] Nom de la révision Cloud Run : __________________
- [ ] Tag Cloud Run (si applicable) : _________________
- [ ] But du déploiement (une phrase) : _______________

### 2. Fichiers modifiés

- [ ] Liste des fichiers source modifiés :
  - ________________________________________________
  - ________________________________________________
  - ________________________________________________
- [ ] Aucun fichier sensible (`.env`, certificats, clés) n’est inclus.
- [ ] Les fichiers de build (`android-app/build/*`) sont exclus du déploiement Cloud Run.

### 3. Fichiers debug attendus dans l’image Docker

- [ ] `static/debug/speech_test.html` présent dans le working dir.
- [ ] `static/guardian.html` présent.
- [ ] `static/auth.js` présent (si applicable).
- [ ] Vérification locale :
  ```bash
  ls -la static/debug/speech_test.html
  ls -la static/guardian.html
  ls -la static/auth.js
  ```

### 4. URLs testées en local

Avant déploiement, lancer localement :

```bash
cd /home/ludo/luna-server
python3 luna_web.py
```

Puis vérifier :

- [ ] `curl -i https://localhost:8888/guardian` → HTTP 200
- [ ] `curl -i https://localhost:8888/static/debug/speech_test.html` → HTTP 200
- [ ] `curl -i https://localhost:8888/static/auth.js` → HTTP 200 (si applicable)
- [ ] `curl -i -X POST https://localhost:8888/api/auth/login` → HTTP 400/401/200 (selon payload)
- [ ] `curl -i https://localhost:8888/api/app/version` → HTTP 200

### 5. Déploiement Cloud Run

- [ ] Commande utilisée :
  ```bash
  gcloud run deploy luna-beta --source=. --region=europe-west1 \
    --project=crypto-parser-475411-k4 --no-traffic \
    --revision-suffix=_____________ --quiet
  ```
- [ ] Déploiement terminé sans erreur.
- [ ] URL de la nouvelle révision notée : ___________________________

### 6. Mise à jour du tag (si trace ou phase-a-auth)

- [ ] Commande de mise à jour du tag :
  ```bash
  gcloud run services update-traffic luna-beta --region=europe-west1 \
    --project=crypto-parser-475411-k4 \
    --to-revisions=luna-beta-00970-bad=100 \
    --update-tags=TAG=NOM-REVISION
  ```
- [ ] Tag mis à jour vérifié avec :
  ```bash
  gcloud run services describe luna-beta --region=europe-west1 \
    --project=crypto-parser-475411-k4 --format='value(traffic)'
  ```

### 7. Vérifications post-déploiement

- [ ] `curl -i https://trace---luna-beta-gly3g647na-ew.a.run.app/guardian` → HTTP 200
- [ ] `curl -i https://trace---luna-beta-gly3g647na-ew.a.run.app/static/debug/speech_test.html` → HTTP 200
- [ ] `curl -i https://trace---luna-beta-gly3g647na-ew.a.run.app/static/auth.js` → HTTP 200 (si applicable)
- [ ] `curl -i https://trace---luna-beta-gly3g647na-ew.a.run.app/api/app/version` → HTTP 200
- [ ] Le contenu de `guardian.html` contient les logs attendus (grep `diagLog`).
- [ ] Le contenu de `speech_test.html` est complet (vérif rapide du titre).

### 8. Validation terrain (à faire par l’utilisateur)

- [ ] Vider le cache de l’APK.
- [ ] Ouvrir Luna → Guardian.
- [ ] Vérifier que le diagnostic natif (long-press) affiche la bonne URL.
- [ ] Lancer le Speech Test et vérifier qu’il s’ouvre.
- [ ] Copier le journal et le transmettre.

### 9. Rollback

- [ ] Commande de rollback identifiée :
  ```bash
  gcloud run services update-traffic luna-beta --region=europe-west1 \
    --project=crypto-parser-475411-k4 \
    --to-revisions=luna-beta-00970-bad=100 \
    --update-tags=trace=ANCIENNE-REVISION
  ```

---

## Règle d’or

> **Aucun déploiement n’est validé tant que les 7 premières étapes ne sont pas cochées et documentées.**
