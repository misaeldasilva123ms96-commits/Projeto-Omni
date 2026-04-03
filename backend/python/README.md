# Python Adapter

Este diretÃ³rio contÃ©m o adapter que conecta a API Rust ao engine Python jÃ¡ existente em `claw-code-main/src`.

## Teste rÃ¡pido

```powershell
cd "C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\backend\python"
python -m app.chat_adapter "{\"message\":\"teste\"}"
```

## EstratÃ©gia

- curto prazo: `subprocess` entre Rust e Python
- mÃ©dio prazo: migrar para `pyo3` se houver necessidade de menor latÃªncia

