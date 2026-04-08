use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde_json::json;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("invalid request: {0}")]
    InvalidRequest(String),
    #[error("python process failed: {message}")]
    PythonProcess {
        code: &'static str,
        message: String,
        stderr: Option<String>,
    },
    #[error("internal error: {0}")]
    Internal(String),
}

impl AppError {
    pub fn python_process(
        code: &'static str,
        message: impl Into<String>,
        stderr: Option<String>,
    ) -> Self {
        Self::PythonProcess {
            code,
            message: message.into(),
            stderr,
        }
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let status = match &self {
            Self::InvalidRequest(_) => StatusCode::BAD_REQUEST,
            Self::PythonProcess { .. } => StatusCode::INTERNAL_SERVER_ERROR,
            Self::Internal(_) => StatusCode::INTERNAL_SERVER_ERROR,
        };

        let body = match self {
            Self::InvalidRequest(message) => Json(json!({
                "error": format!("invalid request: {message}"),
                "code": "invalid_request",
            })),
            Self::PythonProcess { code, message, stderr } => Json(json!({
                "error": format!("python process failed: {message}"),
                "code": code,
                "details": {
                    "stderr": stderr,
                },
            })),
            Self::Internal(message) => Json(json!({
                "error": format!("internal error: {message}"),
                "code": "internal_error",
            })),
        };

        (status, body).into_response()
    }
}
