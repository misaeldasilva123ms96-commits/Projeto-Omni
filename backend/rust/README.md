# Rust API

API HTTP em Axum para expor o engine Python.

## Rodar

```powershell
cd "C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\backend\rust"
cargo run
```

## Endpoints

- `GET /health`
- `POST /chat`

## Exemplo com curl

```powershell
curl -Method POST "http://localhost:3001/chat" `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"message":"ola mundo"}'
```

