# Auto-update — Amigurumi AI

Amigurumi AI usa un aggiornamento automatico Windows basato su GitHub Releases. L'utente non deve reinstallare manualmente ogni nuova versione.

## Flusso utente

```text
Avvio AmigurumiAI.exe
        |
        v
manifest HTTPS pubblico
        |
        v
versione remota > versione locale?
        |
       sì
        v
AmigurumiAI-Updater.exe
        |
        v
download installer + verifica SHA-256
        |
        v
chiusura della vecchia app
        |
        v
installazione silenziosa
        |
        v
riapertura automatica dell'app
```

Dal punto di vista dell'utente, quindi, un aggiornamento del backend richiede un riavvio automatico dell'app; non è necessario usare CMD o reinstallare manualmente.

## Pubblicazione automatica

Il workflow `release-windows.yml` costruisce l'installer quando viene creato un tag `vX.Y.Z`, pubblica la GitHub Release, calcola lo SHA-256 reale e aggiorna `update-manifest.json`.

Il workflow `auto-tag.yml` completa il ciclo: quando viene pubblicato codice applicativo su `main`, legge `APP_VERSION` da `desktop.py` e crea automaticamente il tag `vX.Y.Z` se non esiste ancora. Questo attiva la build Windows e la pubblicazione della release.

Quindi il normale ciclo di sviluppo è:

```text
modifica codice + push su main
        ↓
auto-tag
        ↓
GitHub Actions build Windows
        ↓
installer + SHA-256
        ↓
GitHub Release
        ↓
update-manifest.json
        ↓
installazioni esistenti rilevano l'update
```

## Sicurezza

Il client accetta esclusivamente installer HTTPS e richiede uno SHA-256 esadecimale di 64 caratteri. L'updater verifica l'hash prima di eseguire l'installer.

## Primo bootstrap

Per ricevere gli aggiornamenti automatici, una installazione deve provenire da una release che includa `AmigurumiAI-Updater.exe`. L'updater viene poi aggiornato insieme all'app.
