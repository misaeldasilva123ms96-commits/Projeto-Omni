use glob::Pattern;
use serde::{Deserialize, Serialize};
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

#[derive(Debug, Clone, Serialize)]
pub struct ReadFileOutput {
    #[serde(rename = "filePath")]
    pub file_path: String,
    pub content: String,
    pub offset: usize,
    pub limit: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct GlobSearchOutput {
    pub filenames: Vec<String>,
    #[serde(rename = "numFiles")]
    pub num_files: usize,
    pub truncated: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct GrepSearchInput {
    pub pattern: String,
    #[serde(default = "default_dot")]
    pub path: String,
    #[serde(default)]
    pub limit: Option<usize>,
}

#[derive(Debug, Clone, Serialize)]
pub struct GrepMatch {
    pub path: String,
    pub line_number: usize,
    pub line: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct GrepSearchOutput {
    pub matches: Vec<GrepMatch>,
    #[serde(rename = "numMatches")]
    pub num_matches: usize,
    pub truncated: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct WriteFileOutput {
    #[serde(rename = "filePath")]
    pub file_path: String,
    pub bytes_written: usize,
}

fn default_dot() -> String {
    ".".to_string()
}

fn resolve_base_path(base_path: Option<&str>) -> PathBuf {
    match base_path {
        Some(path) if !path.trim().is_empty() => PathBuf::from(path),
        _ => PathBuf::from("."),
    }
}

fn normalize_path(path: &Path) -> String {
    path.to_string_lossy().replace('\\', "/")
}

pub fn read_file(path: &str, offset: Option<usize>, limit: Option<usize>) -> io::Result<ReadFileOutput> {
    let content = fs::read_to_string(path)?;
    let start = offset.unwrap_or(0).min(content.len());
    let requested_limit = limit.unwrap_or(4000);
    let end = (start + requested_limit).min(content.len());
    Ok(ReadFileOutput {
        file_path: normalize_path(Path::new(path)),
        content: content[start..end].to_string(),
        offset: start,
        limit: requested_limit,
    })
}

pub fn glob_search(pattern: &str, base_path: Option<&str>) -> io::Result<GlobSearchOutput> {
    let base = resolve_base_path(base_path);
    let glob_pattern = Pattern::new(pattern).map_err(io::Error::other)?;
    let mut filenames = Vec::new();

    for entry in WalkDir::new(&base).into_iter().filter_map(Result::ok) {
        let path = entry.path();
        if path == base {
            continue;
        }
        let relative = path.strip_prefix(&base).unwrap_or(path);
        if glob_pattern.matches_path(relative) {
            filenames.push(normalize_path(path));
        }
    }

    let truncated = filenames.len() > 100;
    if truncated {
        filenames.truncate(100);
    }

    Ok(GlobSearchOutput {
        num_files: filenames.len(),
        filenames,
        truncated,
    })
}

pub fn grep_search(input: &GrepSearchInput) -> io::Result<GrepSearchOutput> {
    let base = resolve_base_path(Some(&input.path));
    let mut matches = Vec::new();
    let limit = input.limit.unwrap_or(50);
    let needle = input.pattern.to_lowercase();

    for entry in WalkDir::new(&base).into_iter().filter_map(Result::ok) {
        if !entry.file_type().is_file() {
            continue;
        }
        let path = entry.path();
        let Ok(content) = fs::read_to_string(path) else {
            continue;
        };

        for (index, line) in content.lines().enumerate() {
            if line.to_lowercase().contains(&needle) {
                matches.push(GrepMatch {
                    path: normalize_path(path),
                    line_number: index + 1,
                    line: line.to_string(),
                });
                if matches.len() >= limit {
                    return Ok(GrepSearchOutput {
                        num_matches: matches.len(),
                        matches,
                        truncated: true,
                    });
                }
            }
        }
    }

    Ok(GrepSearchOutput {
        num_matches: matches.len(),
        matches,
        truncated: false,
    })
}

pub fn write_file(path: &str, content: &str) -> io::Result<WriteFileOutput> {
    if let Some(parent) = Path::new(path).parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)?;
        }
    }
    fs::write(path, content)?;
    Ok(WriteFileOutput {
        file_path: normalize_path(Path::new(path)),
        bytes_written: content.len(),
    })
}
