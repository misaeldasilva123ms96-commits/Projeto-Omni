use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PermissionMode {
    Allow,
    Deny,
    Prompt,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PermissionRequest {
    pub tool_name: String,
    pub input: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PermissionPromptDecision {
    Allow,
    Deny { reason: String },
}

pub trait PermissionPrompter {
    fn decide(&mut self, request: &PermissionRequest) -> PermissionPromptDecision;
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PermissionOutcome {
    Allow,
    Deny { reason: String },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PermissionPolicy {
    default_mode: PermissionMode,
    tool_modes: BTreeMap<String, PermissionMode>,
}

impl PermissionPolicy {
    #[must_use]
    pub fn new(default_mode: PermissionMode) -> Self {
        Self {
            default_mode,
            tool_modes: BTreeMap::new(),
        }
    }

    #[must_use]
    pub fn with_tool_mode(mut self, tool_name: impl Into<String>, mode: PermissionMode) -> Self {
        self.tool_modes.insert(tool_name.into(), mode);
        self
    }

    #[must_use]
    pub fn authorize(
        &self,
        tool_name: &str,
        input: &str,
        mut prompter: Option<&mut dyn PermissionPrompter>,
    ) -> PermissionOutcome {
        let mode = self
            .tool_modes
            .get(tool_name)
            .copied()
            .unwrap_or(self.default_mode);

        match mode {
            PermissionMode::Allow => PermissionOutcome::Allow,
            PermissionMode::Deny => PermissionOutcome::Deny {
                reason: format!("tool '{tool_name}' denied by permission policy"),
            },
            PermissionMode::Prompt => match prompter.as_mut() {
                Some(prompt) => match prompt.decide(&PermissionRequest {
                    tool_name: tool_name.to_string(),
                    input: input.to_string(),
                }) {
                    PermissionPromptDecision::Allow => PermissionOutcome::Allow,
                    PermissionPromptDecision::Deny { reason } => PermissionOutcome::Deny { reason },
                },
                None => PermissionOutcome::Deny {
                    reason: format!("tool '{tool_name}' requires interactive approval"),
                },
            },
        }
    }
}
