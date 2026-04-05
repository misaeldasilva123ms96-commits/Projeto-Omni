#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Session {
    pub version: u32,
    pub messages: Vec<String>,
}

impl Session {
    #[must_use]
    pub fn new() -> Self {
        Self {
            version: 1,
            messages: Vec::new(),
        }
    }
}

impl Default for Session {
    fn default() -> Self {
        Self::new()
    }
}
