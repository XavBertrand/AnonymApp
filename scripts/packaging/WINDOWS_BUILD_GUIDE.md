# Windows Build Guide

Ce guide décrit le flux pratique pour :

1. préparer un dossier de release depuis WSL
2. le copier sur Windows
3. générer l'exécutable Windows avec l'environnement Python `py311_llm`
4. faire les premiers tests de lancement

Le build final de l'exe doit être fait sur Windows. PyInstaller ne cross-compile pas correctement depuis WSL/Linux.

## Pré-requis

### Côté WSL

- dépôt à jour
- environnement Python du repo utilisable
- dossier `models/` présent et non vide
- idéalement le modèle GLiNER déjà placé dans :
  - `models/gliner_multi_pii_v1/`

### Côté Windows

- Miniforge/Conda installé
- environnement Python existant :
  - `C:\Users\bertr\miniforge3\envs\py311_llm\python.exe`
- PowerShell

## 1. Préparer la release depuis WSL

Depuis la racine du repo :

```bash
source .venv/bin/activate
python3 scripts/packaging/prepare_windows_test_release.py
```

Si tu veux seulement restager sans relancer les tests ciblés :

```bash
python3 scripts/packaging/prepare_windows_test_release.py --skip-tests
```

Le script :

- vérifie les fichiers requis
- vérifie que `models/` est présent et non vide
- exécute les tests ciblés de packaging/smoke
- génère `out/windows_test_release/`
- écrit :
  - `build_info.json`
  - `commit.txt`
  - `next_steps_windows.txt`

## 2. Copier le dossier sur Windows

Copie le dossier suivant sur la machine Windows :

```text
out/windows_test_release
```

Exemple de destination :

```text
C:\Users\bertr\AnonymApp\windows_test_release
```

## 3. Ouvrir PowerShell sur Windows

Ouvre PowerShell dans le dossier copié :

```powershell
cd C:\Users\bertr\AnonymApp\windows_test_release
```

## 4. Lancer le build Windows avec `py311_llm`

Commande recommandée :

```powershell
powershell -ExecutionPolicy Bypass -File scripts/packaging/build_windows.ps1 -PythonExe C:\Users\bertr\miniforge3\envs\py311_llm\python.exe
```

Cette commande :

- vérifie le dossier stagé
- crée `.venv-windows-build` si nécessaire
- installe le projet dans ce venv de build
- installe `PyInstaller`
- construit l'application portable
- affiche les DLL runtime Conda détectées et bundlées

## 5. Emplacement de sortie attendu

Après succès, l'exécutable doit être ici :

```text
dist\a4_desktop_portable\A4Desktop.exe
```

Le script affiche aussi :

- le chemin du bundle portable
- le chemin exact de l'exécutable

## 6. Tester le lancement

Depuis PowerShell :

```powershell
dist\a4_desktop_portable\A4Desktop.exe
```

## 7. Vérifications immédiates après build

Vérifie les points suivants :

- l'application démarre
- une fenêtre desktop apparaît
- il n'y a plus d'erreur `_sqlite3`
- le script affiche bien les DLL Conda résolues
- `models/` est présent à côté de l'application packagée

## 8. Si l'application tourne mais n'affiche rien

Depuis les derniers correctifs, Windows ne doit plus forcer `QT_QPA_PLATFORM=offscreen`.

Si le process apparaît dans le Task Manager mais sans fenêtre :

1. ferme le process
2. rebuild avec la commande ci-dessus
3. relance `A4Desktop.exe`
4. regarde les logs éventuels dans :

```text
runtime\logs\anonymapp.log
```

selon l'endroit depuis lequel l'application est lancée

## 9. Si le build échoue sur les DLL

Le script cherche explicitement ces DLL dans l'environnement Conda/Miniforge actif :

- `sqlite3.dll`
- `libcrypto-3-x64.dll`
- `libssl-3-x64.dll`
- `ffi-8.dll`
- `libexpat.dll`
- `liblzma.dll`
- `libbz2.dll`

Sources recherchées côté Windows :

- `%CONDA_PREFIX%\Library\bin`
- `sys.base_prefix\Library\bin`
- `sys.prefix\Library\bin`
- puis aussi :
  - `DLLs`
  - `bin`
  - racine de l'env

## 10. Commandes résumées

### WSL

```bash
source .venv/bin/activate
python3 scripts/packaging/prepare_windows_test_release.py
```

### Windows

```powershell
cd C:\Users\bertr\AnonymApp\windows_test_release
powershell -ExecutionPolicy Bypass -File scripts/packaging/build_windows.ps1 -PythonExe C:\Users\bertr\miniforge3\envs\py311_llm\python.exe
dist\a4_desktop_portable\A4Desktop.exe
```
