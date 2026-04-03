# Omni Project Integration

Este workspace integra:

- backend em Rust para expor a API HTTP
- engine Python para runtime e tools
- frontend React para Web App
- camada mobile com Capacitor para gerar APK Android

## Estrutura

```text
project/
â”œâ”€â”€ README.md
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ python/
â”‚   â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ chat_adapter.py
â”‚   â”‚   â”‚   â””â”€â”€ requirements.txt
â”‚   â”‚   â””â”€â”€ README.md
â”‚   â””â”€â”€ rust/
â”‚       â”œâ”€â”€ Cargo.toml
â”‚       â”œâ”€â”€ .env.example
â”‚       â”œâ”€â”€ src/
â”‚       â”‚   â”œâ”€â”€ error.rs
â”‚       â”‚   â””â”€â”€ main.rs
â”‚       â””â”€â”€ README.md
â””â”€â”€ frontend/
    â”œâ”€â”€ mobile/
    â”‚   â”œâ”€â”€ capacitor.config.ts
    â”‚   â”œâ”€â”€ package.json
    â”‚   â””â”€â”€ README.md
    â””â”€â”€ web/
        â”œâ”€â”€ index.html
        â”œâ”€â”€ package.json
        â”œâ”€â”€ tsconfig.json
        â”œâ”€â”€ tsconfig.node.json
        â”œâ”€â”€ vite.config.ts
        â””â”€â”€ src/
            â”œâ”€â”€ App.tsx
            â”œâ”€â”€ main.tsx
            â”œâ”€â”€ styles.css
            â”œâ”€â”€ types.ts
            â””â”€â”€ vite-env.d.ts
```

## Arquitetura

Fluxo principal:

```text
React Web / Capacitor Mobile
        |
        v
 Rust API (Axum)
        |
        v
 Python Adapter
        |
        v
 QueryEnginePort + tools/runtime existentes
```

### DecisÃ£o tÃ©cnica

- `Rust + Axum`: API performÃ¡tica, tipada, com CORS, logs e boa base para streaming.
- `Python via subprocess`: integraÃ§Ã£o inicial mais simples e estÃ¡vel para tools dinÃ¢micas.
- `React + Vite`: bootstrap rÃ¡pido para o chat web.
- `Capacitor`: caminho mais curto para transformar o app web em APK Android.

## Etapa 1 â€” Backend Rust

### 1. Entrar no backend

```powershell
cd "C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\backend\rust"
```

### 2. Rodar a API

```powershell
cargo run
```

API padrÃ£o:

- `POST http://localhost:3001/chat`
- `GET http://localhost:3001/health`

### 3. JSON esperado

Request:

```json
{
  "message": "Explique esta arquitetura"
}
```

Response:

```json
{
  "response": "Prompt: Explique esta arquitetura\nMatched commands: none\nMatched tools: none\nPermission denials: 0",
  "session_id": "abc123",
  "source": "python-query-engine"
}
```

### 4. VariÃ¡veis de ambiente

Copie `.env.example` para `.env` se quiser customizar:

```powershell
Copy-Item .env.example .env
```

## Etapa 2 â€” Python Engine

### 1. Entrar no adapter Python

```powershell
cd "C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\backend\python"
```

### 2. Testar manualmente o adapter

```powershell
python -m app.chat_adapter "{\"message\":\"teste de integraÃ§Ã£o\"}"
```

### 3. O que o adapter faz

- lÃª a mensagem enviada pelo Rust
- injeta o path do engine Python existente em `claw-code-main/src`
- instancia `QueryEnginePort`
- retorna JSON para a API Rust

## Etapa 3 â€” Frontend Web

### 1. Instalar dependÃªncias

```powershell
cd "C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\frontend\web"
npm install
```

### 2. Rodar em modo dev

```powershell
npm run dev
```

### 3. Funcionalidades incluÃ­das

- chat estilo ChatGPT
- histÃ³rico salvo em `localStorage`
- indicador de loading
- mensagens do usuÃ¡rio e do assistente
- consumo da API Rust em `http://localhost:3001/chat`

## Etapa 4 â€” APK com Capacitor

### 1. Build do React

```powershell
cd "C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\frontend\web"
npm run build
```

### 2. Instalar dependÃªncias mobile

```powershell
cd "C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\frontend\mobile"
npm install
```

### 3. Adicionar Android

```powershell
npx cap add android
```

### 4. Sincronizar assets do web

```powershell
npx cap sync android
```

### 5. Abrir no Android Studio

```powershell
npx cap open android
```

### 6. Gerar APK

No Android Studio:

1. `Build`
2. `Build Bundle(s) / APK(s)`
3. `Build APK(s)`

## Etapa 5 â€” Deploy

### Frontend na Vercel

```powershell
cd "C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\frontend\web"
vercel
```

### Backend no Railway ou Render

Use o diretÃ³rio:

```text
project/backend/rust
```

Comando de start:

```powershell
cargo run --release
```

## Erros comuns e soluÃ§Ãµes

### Erro: `python not found`

SoluÃ§Ã£o:

- instalar Python 3.11+
- validar com `python --version`
- se necessÃ¡rio, configurar `PYTHON_BIN` no backend Rust

### Erro: `address already in use`

SoluÃ§Ã£o:

- mudar `APP_PORT` no `.env`
- ou encerrar o processo que jÃ¡ usa a porta `3001`

### Erro: CORS no frontend

SoluÃ§Ã£o:

- conferir se a API Rust estÃ¡ rodando
- validar se `CorsLayer::permissive()` estÃ¡ ativo
- manter o frontend chamando exatamente `http://localhost:3001/chat`

### Erro: `npx cap add android` falha

SoluÃ§Ã£o:

- instalar Android Studio
- instalar Android SDK
- confirmar `JAVA_HOME`
- rodar `npx cap doctor`

### Erro: app mobile nÃ£o carrega a API local

SoluÃ§Ã£o:

- em emulador Android, trocar `localhost` por `10.0.2.2`
- ou expor a API em uma URL de rede local

## PrÃ³ximas melhorias

- autenticaÃ§Ã£o com JWT
- banco para histÃ³rico e sessÃµes
- streaming com SSE ou WebSocket
- voz usando Web Speech API e plugins nativos
- sistema de plugins carregÃ¡veis no backend
- troca de `subprocess` por `pyo3` quando a integraÃ§Ã£o estiver mais madura

