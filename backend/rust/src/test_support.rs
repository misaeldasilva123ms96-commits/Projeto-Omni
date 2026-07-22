use std::{
    env,
    ffi::{OsStr, OsString},
    sync::{Mutex, MutexGuard, OnceLock},
};

static ENV_TEST_LOCK: OnceLock<Mutex<()>> = OnceLock::new();

pub(crate) struct EnvTestGuard {
    saved: Vec<(String, Option<OsString>)>,
    _lock: MutexGuard<'static, ()>,
}

impl EnvTestGuard {
    pub(crate) fn new(keys: &[&str]) -> Self {
        let lock = ENV_TEST_LOCK.get_or_init(|| Mutex::new(()));
        let guard = lock.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
        let saved = keys
            .iter()
            .map(|key| ((*key).to_string(), env::var_os(key)))
            .collect();
        Self {
            saved,
            _lock: guard,
        }
    }

    pub(crate) fn set(&self, key: &str, value: impl AsRef<OsStr>) {
        env::set_var(key, value);
    }

    pub(crate) fn remove(&self, key: &str) {
        env::remove_var(key);
    }
}

impl Drop for EnvTestGuard {
    fn drop(&mut self) {
        for (key, value) in self.saved.drain(..) {
            match value {
                Some(value) => env::set_var(key, value),
                None => env::remove_var(key),
            }
        }
    }
}
