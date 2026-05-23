# OpenClaude + Codex + VS Code no Windows

## Visao geral

Este workspace foi preparado para usar:

- VS Code como ambiente central
- Codex no VS Code via extensao `openai.chatgpt`
- OpenClaude no terminal integrado e na extensao `OpenClaude`
- o diretorio atual como pasta principal de operacao

Arquitetura local:

- `openclaude` roda pelo launcher em `C:\Users\Misael\.local\bin\openclaude.cmd`
- o pacote npm instalado fica em `C:\Users\Misael\AppData\Roaming\npm\node_modules\@gitlawb\openclaude`
- `ripgrep` foi instalado via Scoop e responde por `rg`
- a extensao do OpenClaude foi instalada a partir do codigo-fonte do repositorio oficial
- as tasks do VS Code chamam scripts PowerShell do proprio workspace

## Estado validado neste setup

- `node -v` -> `v24.14.1`
- `npm -v` -> `11.11.0`
- `git --version` -> `git version 2.53.0.windows.2`
- `code --version` -> `1.114.0`
- `rg --version` -> `ripgrep 15.1.0`
- `openclaude --version` -> `0.1.7 (Open Claude)`
- `bun --version` -> nao instalado

## O que foi instalado

### OpenClaude CLI

Instalacao escolhida:

```powershell
cmd /c npm install -g @gitlawb/openclaude
```

Motivo:

- a instalacao do pacote funcionou
- o build por source com Bun nao foi necessario
- no Windows, o shim global do npm nao ficou utilizavel
- por isso foi criado um launcher estavel em `C:\Users\Misael\.local\bin\openclaude.cmd`

Teste rapido:

```powershell
openclaude --version
```

### ripgrep

Foi necessario instalar o `ripgrep` fora do pacote do Codex porque o `rg.exe` empacotado pela app do Codex falhava com `Acesso negado`.

Instalacao escolhida:

```powershell
cmd /c scoop install ripgrep
```

Teste rapido:

```powershell
rg --version
```

### Extensoes do VS Code

Instaladas:

- `openai.chatgpt`
- `devnull-bootloader.openclaude-vscode`

Observacao:

- a extensao do OpenClaude nao estava publicada no marketplace no momento do setup
- por isso ela foi empacotada do repositorio oficial em `vendor/openclaude-upstream/vscode-extension/openclaude-vscode`

Repetir instalacao da extensao:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-openclaude-vscode-extension.ps1
```

## Estrutura criada

- `.env.openclaude.example`: exemplo seguro de variaveis de ambiente
- `config/examples/claude-settings.example.json`: template de roteamento de agentes
- `scripts/openclaude-common.ps1`: funcoes compartilhadas para launcher e validacao
- `scripts/start-openclaude-openai.ps1`: inicia OpenClaude com OpenAI-compatible
- `scripts/start-openclaude-codex.ps1`: inicia OpenClaude com credenciais do Codex
- `scripts/start-openclaude-ollama.ps1`: inicia OpenClaude com Ollama local
- `scripts/openclaude-doctor.ps1`: diagnostico do ambiente
- `scripts/install-openclaude-vscode-extension.ps1`: reinstala a extensao do OpenClaude
- `tests/tooling/openclaude-smoke.test.ps1`: smoke test do tooling
- `.vscode/tasks.json`: atalhos operacionais no VS Code
- `.vscode/settings.json`: configuracao do workspace para terminal e OpenClaude
- `.vscode/extensions.json`: recomendacoes de extensoes

## Como iniciar cada modo

### 1. OpenAI

1. Copie o arquivo de exemplo:

```powershell
Copy-Item .\.env.openclaude.example .\.env.openclaude.local
```

2. Edite `.\.env.openclaude.local` e preencha:

```powershell
OPENAI_API_KEY=COLOCAR_CHAVE_AQUI
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=https://api.openai.com/v1
```

3. Inicie:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-openclaude-openai.ps1
```

Ou use a task do VS Code:

- `Tasks: Run Task` -> `OpenClaude: Start OpenAI`

### 2. Codex

O melhor fluxo no seu ambiente atual e:

- manter o Codex no VS Code pela extensao `openai.chatgpt`
- usar o OpenClaude no terminal com backend Codex quando quiser o mesmo backend em modo CLI

Seu ambiente ja possui `C:\Users\Misael\.codex\auth.json`, entao o launcher tenta reutilizar essa autenticacao automaticamente.

Iniciar:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-openclaude-codex.ps1
```

Ou no VS Code:

- `Tasks: Run Task` -> `OpenClaude: Start Codex`

Se quiser forcar outro arquivo de credenciais:

```powershell
$env:CODEX_AUTH_JSON_PATH="C:\caminho\auth.json"
powershell -ExecutionPolicy Bypass -File .\scripts\start-openclaude-codex.ps1
```

### 3. Ollama

Pre-requisitos:

- Ollama instalado
- servico local respondendo em `http://localhost:11434`
- um modelo ja puxado, por exemplo:

```powershell
ollama pull qwen2.5-coder:7b
```

Iniciar:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-openclaude-ollama.ps1
```

Ou no VS Code:

- `Tasks: Run Task` -> `OpenClaude: Start Ollama`

## Roteamento inteligente de agentes

O template seguro esta em:

- `config/examples/claude-settings.example.json`

Copie manualmente para o local privado:

```powershell
New-Item -ItemType Directory -Force -Path $HOME\.claude | Out-Null
Copy-Item .\config\examples\claude-settings.example.json $HOME\.claude\settings.json
```

Depois substitua os placeholders da chave antes de usar.

Roteamento inicial sugerido:

- `Explore` -> `gpt-4.1-mini`
- `Plan` -> `gpt-4o`
- `general-purpose` -> `gpt-4o`
- `frontend-dev` -> `gpt-4.1-mini`
- `default` -> `gpt-4o`

Observacao importante:

- `~/.claude/settings.json` pode guardar `api_key` em texto puro
- nao commite esse arquivo
- por seguranca, o template fica no repo e a copia real fica fora dele

## Fluxo recomendado no VS Code

### Codex no chat/agente

- abra esta pasta no VS Code
- confirme a extensao `openai.chatgpt`
- use o painel/chat do Codex para discussao, planejamento e alteracoes no editor

### OpenClaude no terminal integrado

- abra o terminal integrado no mesmo workspace
- rode uma das tasks `OpenClaude: Start ...`
- ou use a Activity Bar da extensao OpenClaude

### Mesmo projeto, sem conflito

- o `cwd` do terminal integrado foi fixado para `${workspaceFolder}`
- as tasks usam `${workspaceFolder}` explicitamente
- os dois agentes apontam para a mesma pasta de projeto

## Seguranca e boas praticas

Fica no repositorio:

- scripts de inicializacao
- tasks e settings do VS Code
- templates sem segredos
- documentacao operacional

Fica fora do repositorio:

- `.env.openclaude.local`
- `.openclaude-profile.json`
- `~/.claude/settings.json`
- qualquer arquivo com API key ou token

Protecoes aplicadas:

- `.gitignore` atualizado para secrets e perfis privados
- `.vscode` configurado para versionar apenas os arquivos do workspace
- nenhum token foi salvo em arquivo do projeto
- o template de roteamento usa placeholders

Nao habilitado por padrao:

- bypass de permissoes de agentes
- flags experimentais
- chaves em texto puro dentro do projeto

## Diagnostico e verificacao

Doctor:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\openclaude-doctor.ps1
```

Smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File .\tests\tooling\openclaude-smoke.test.ps1
```

Task equivalente:

- `OpenClaude: Doctor/Check`
- `OpenClaude: Smoke Test`

## Teste funcional sugerido

Depois de iniciar o OpenClaude em qualquer provider valido, use este prompt:

```text
Analise a estrutura deste projeto, identifique a organizacao entre backend, frontend e scripts, sugira uma pequena refatoracao de baixo risco e aplique uma alteracao simples em um arquivo de teste ou tooling sem tocar em secrets.
```

Resultado esperado:

- o agente descreve a estrutura geral do projeto
- sugere uma melhoria pequena e de baixo risco
- altera um arquivo de teste ou tooling
- mostra diff claro e sem tocar em credenciais

## Troubleshooting

### `openclaude` nao abre

Teste:

```powershell
where openclaude
openclaude --version
```

Se necessario, reinstale:

```powershell
cmd /c npm install -g @gitlawb/openclaude
```

### `rg --version` falha

Reinstale via Scoop:

```powershell
cmd /c scoop install ripgrep
```

### Extensao OpenClaude ausente no VS Code

Reinstale pelo script local:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-openclaude-vscode-extension.ps1
```

### OpenAI falha por chave ausente

Garanta que `.env.openclaude.local` exista e contenha:

```powershell
OPENAI_API_KEY=COLOCAR_CHAVE_AQUI
```

### Ollama nao conecta

Valide:

```powershell
ollama --version
Test-NetConnection localhost -Port 11434
ollama list
```

### Bun nao existe

Bun nao e necessario para o caminho escolhido neste setup.

Se voce quiser build por source futuramente:

```powershell
powershell -c "irm bun.sh/install.ps1 | iex"
bun --version
```

## Atualizacao futura

### Atualizar OpenClaude CLI

```powershell
cmd /c npm install -g @gitlawb/openclaude@latest
openclaude --version
```

### Atualizar extensao OpenClaude por source

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-openclaude-vscode-extension.ps1
```

### Revisar roteamento

- ajuste `config/examples/claude-settings.example.json`
- copie novamente para `~/.claude/settings.json`
- nunca commite o arquivo real

## Checklist final

- `openclaude --version` responde
- `rg --version` responde
- `code --list-extensions` mostra `openai.chatgpt`
- `code --list-extensions` mostra `devnull-bootloader.openclaude-vscode`
- `.env.openclaude.local` criado com suas credenciais
- task `OpenClaude: Doctor/Check` passa
- task `OpenClaude: Start OpenAI`, `Start Codex` ou `Start Ollama` abre no terminal integrado
- `~/.claude/settings.json` existe apenas fora do repo, se voce optar por agent routing
