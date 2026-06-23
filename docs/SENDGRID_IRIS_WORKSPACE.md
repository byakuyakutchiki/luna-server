# SendGrid — Infrastructure email Iris Workspace

**Objectif :** envoi des exports PDF/Word du dossier final Iris par email.
**Date :** 2026-06-24
**Statut :** code livré et déployé. Reste à fournir la clé SendGrid (côté Ludo).

---

## 1. Architecture (service email unique réutilisable)

Un seul service email partagé par toute l'application : **`EmailClient`**
(`integrations/email/email_client.py`), instancié une fois en global
(`email_client = EmailClient.from_env()` dans `luna_web.py`).

```
Frontend (team_workspace.html / workspace.html)
   sendIrisReport(fmt)  ──POST──>  /api/team/report/send
                                        │
                                        ├─ _iris_build_report(md, fmt)   (helper DRY)
                                        │     ├─ PDF  : fpdf2
                                        │     └─ DOCX : python-docx
                                        │
                                        └─ email_client.send(to, subject, attachments=[fichier])
                                              ├─ FOUNDATION_TEST_MODE=true → simulé (aucun envoi)
                                              ├─ SENDGRID_API_KEY absente   → désactivé (erreur gracieuse)
                                              └─ sinon                       → envoi réel via SendGrid
```

**Exigences couvertes :**
| Exigence | Statut | Où |
|---|---|---|
| Envoi PDF/Word par email | ✅ | `POST /api/team/report/send` (`luna_web.py`) |
| Clé API en variable d'env | ✅ | `SENDGRID_API_KEY` lue par `EmailClient.from_env()` |
| Service email unique réutilisable | ✅ | `EmailClient` (global `email_client`) |
| Mode désactivé si clé absente | ✅ | `EmailClient.is_configured` → `send()` retourne `(False, error)` |
| Journalisation des erreurs | ✅ | `EmailClient` (l.175-189) + `iris_report_send` (warning/résumé) |
| Ne pas bloquer l'UI si échec | ✅ | `sendIrisReport` → toast d'erreur, le download/archive restent OK |

---

## 2. Code livré

| Fichier | Changement |
|---|---|
| `luna_web.py` | endpoint `POST /api/team/report/send` + helper `_iris_build_report` + logging |
| `static/team_workspace.html` | `sendIrisReport()` + boutons Distribuer/Envoyer |
| `static/workspace.html` | idem |
| `deploy.sh` | transmission des vars email à Cloud Run |
| `integrations/email/email_client.py` | (existant) service SendGrid — mode test + désactivé + logs |

Le endpoint est public (`/api/team/*` dans `_PUBLIC_PATHS`), génère le document
en mémoire, écrit un fichier temporaire pour la pièce jointe (nettoyé en
`finally`), plafond 200 Ko, max 10 destinataires.

---

## 3. Variables `.env` nécessaires

```bash
# --- Email SendGrid (OBLIGATOIRE pour l'envoi réel) ---
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxx     # clé API SendGrid
LUNA_EMAIL_FROM=iris@ton-domaine-verifie.fr       # expéditeur VÉRIFIÉ dans SendGrid
LUNA_EMAIL_SENDER_NAME=Iris                        # (optionnel) nom affiché

# --- Sécurité tests (optionnel mais recommandé au début) ---
FOUNDATION_TEST_MODE=true   # true = emails simulés (sauvegardés, jamais envoyés)
```

⚠️ `LUNA_EMAIL_FROM` doit être un **expéditeur vérifié** dans SendGrid
(Single Sender ou Domain Authentication), sinon SendGrid refuse l'envoi même
avec une clé valide.

---

## 4. Procédure de déploiement Cloud Run

1. Créer un compte SendGrid (gratuit, 100 mails/j), générer une **API Key**
   (Settings → API Keys → Create, droit *Mail Send*).
2. Vérifier un expéditeur (Settings → Sender Authentication → Single Sender
   Verification, ou authentifier un domaine).
3. Ajouter les variables au `.env` local (source de vérité du déploiement) :
   ```bash
   printf '\nSENDGRID_API_KEY=SG.xxxx\nLUNA_EMAIL_FROM=iris@domaine.fr\nLUNA_EMAIL_SENDER_NAME=Iris\n' >> .env
   # 1re fois, pour simuler sans envoyer :
   printf 'FOUNDATION_TEST_MODE=true\n' >> .env
   ```
4. Déployer :
   ```bash
   ./deploy.sh
   ```
   `deploy.sh` ne transmet que les variables non vides → la clé part sur Cloud Run.
5. Vérifier la révision et l'envoi (cf. §5).
6. Quand validé : passer `FOUNDATION_TEST_MODE=false` (ou le retirer) puis redéployer
   pour activer l'envoi réel.

---

## 5. Tests de validation

### 5.1 Tests unitaires (locaux, sans serveur)
```bash
# Génération PDF/DOCX + mode désactivé
python3 - <<'PY'
import asyncio, os
os.environ.pop("SENDGRID_API_KEY", None); os.environ["FOUNDATION_TEST_MODE"]="false"
from integrations.email.email_client import EmailClient
ec = EmailClient.from_env()
assert ec.is_configured is False
ok, info = asyncio.run(ec.send(to="x@y.com", subject="t", body_text="t"))
assert ok is False and "non configure" in info["error"].lower()
print("OK désactivé : pas d'exception, erreur gracieuse")
PY

# Mode simulé (process neuf)
FOUNDATION_TEST_MODE=true SENDGRID_API_KEY="" python3 -c "
import asyncio; from integrations.email.email_client import EmailClient
ok,info=asyncio.run(EmailClient.from_env().send(to='x@y.com',subject='t',body_text='t'))
assert info['simulated'] is True; print('OK simulé : aucun envoi réel')"
```
**Résultats attendus** (tous obtenus le 2026-06-24) :
- génération PDF (`%PDF-`) + DOCX (zip `PK`) ✅
- sans clé → `is_configured=False`, `send` retourne `(False, "Email non configure")` sans exception ✅
- `FOUNDATION_TEST_MODE=true` → `simulated=True`, fichier dans `tmp/emails/`, aucun envoi ✅

### 5.2 Tests endpoint (prod)
```bash
URL=https://luna-beta-674304336025.europe-west1.run.app
# Validation
curl -sS -X POST $URL/api/team/report/send -H "Content-Type: application/json" -d '{"markdown":"x","to":[]}'  -w " %{http_code}\n"   # → 400 (pas de destinataire)
curl -sS -X POST $URL/api/team/report/send -H "Content-Type: application/json" -d '{"markdown":"","to":["a@b.com"]}' -w " %{http_code}\n" # → 400 (rapport vide)
# Envoi (après config) — remplacer le destinataire
curl -sS -X POST $URL/api/team/report/send -H "Content-Type: application/json" \
  -d '{"markdown":"=== TEST ===\nDécision : OK","format":"pdf","title":"Test","to":["toi@toi.fr"]}'
# Attendu sans clé : {"ok":false,"error":"Email non configure..."}
# Attendu mode test : {"ok":true,"simulated":true,...}
# Attendu réel : {"ok":true,"sent":1,"simulated":false,...} + email reçu
```

### 5.3 Vérification logs Cloud Run
```bash
gcloud run services logs read luna-beta --region=europe-west1 --limit=50 | grep iris_report_send
# → "iris_report_send: 1/1 envoyé(s)" ou "échec envoi vers ... : <raison>"
```

---

## 6. Ce qui reste à faire (côté Ludo)

- [ ] Créer le compte SendGrid + API Key
- [ ] Vérifier un expéditeur (`LUNA_EMAIL_FROM`)
- [ ] Ajouter les 3 variables au `.env`
- [ ] `./deploy.sh`
- [ ] Tester (§5.2) puis basculer `FOUNDATION_TEST_MODE=false` pour le réel

Le code, l'infra et les garde-fous sont en place. Il ne manque que la clé.
