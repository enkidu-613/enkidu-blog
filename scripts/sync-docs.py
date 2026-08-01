#!/usr/bin/env python3
"""Sync teaching docs from source (PyCharmMiscProject/md) to blog posts."""

import os
import re
import glob
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SRC_DIR = "/Users/enkidu/PyCharmMiscProject/md"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DST_DIR = str(REPOSITORY_ROOT / "src" / "content" / "posts")

# Mapping: (source_glob, dst_prefix, number_range)
# Main courses: 00-32
MAIN_MAPPING = [(SRC_DIR, "course", list(range(0, 33)))]

# Subdirectory mappings
SUB_MAPPINGS = [
    (os.path.join(SRC_DIR, "ai学习应用数学"), "math", [1]),
    (os.path.join(SRC_DIR, "工具教学"), "tools", [1, 2, 3]),
    (os.path.join(SRC_DIR, "新手需要学习的前置知识"), "prereq", list(range(0, 28))),
    (os.path.join(SRC_DIR, "编程语言基础"), "language-schema", None),  # special
]


def extract_frontmatter(content):
    """Extract frontmatter from blog post content. Returns (fm_lines, body)."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[1], parts[2]
    return None, content


def source_mtime_date(src_path):
    """Return a source file's modification date in Asia/Shanghai."""
    timestamp = os.path.getmtime(src_path)
    return datetime.fromtimestamp(timestamp, tz=ZoneInfo("Asia/Shanghai")).strftime(
        "%Y-%m-%d"
    )


def update_frontmatter_metadata(frontmatter, published_date, section):
    """Set source metadata and remove obsolete updated metadata."""
    lines = frontmatter.splitlines()
    replacements = {
        "published": f"published: {published_date}",
        "section": f"section: {section}",
    }
    patterns = {
        key: re.compile(rf"^{key}:\s*.*$") for key in replacements
    }
    updated_pattern = re.compile(r"^updated:\s*.*$")
    replaced = set()
    retained_lines = []

    for line in lines:
        if updated_pattern.match(line):
            continue
        matching_key = next(
            (key for key, pattern in patterns.items() if pattern.match(line)), None
        )
        if matching_key is None:
            retained_lines.append(line)
        elif matching_key not in replaced:
            retained_lines.append(replacements[matching_key])
            replaced.add(matching_key)

    for key, line in replacements.items():
        if key not in replaced:
            retained_lines.append(line)

    return "\n".join(retained_lines) + "\n"


def extract_source_body(content):
    """Extract body from source file, stripping the leading # title line."""
    lines = content.split("\n")
    # Strip leading tab if present on first line
    if lines and lines[0].startswith("\t# "):
        lines[0] = lines[0][1:]  # remove leading tab
    # Remove first line if it's a # heading
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    # Remove leading blank lines
    while lines and lines[0].strip() == "":
        lines.pop(0)
    return "\n".join(lines)


def find_source_file(src_dir, num):
    """Find a source file matching the given number prefix."""
    pattern = os.path.join(src_dir, f"{num:02d}_*.md")
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def find_source_file_numeric(src_dir, num):
    """Find a source file matching the given numeric prefix (no zero-padding for single digit)."""
    # Try zero-padded first
    pattern = os.path.join(src_dir, f"{num:02d}_*.md")
    matches = glob.glob(pattern)
    if matches:
        return matches[0]
    # Try single digit
    pattern = os.path.join(src_dir, f"{num}_*.md")
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def sync_file(src_path, dst_path, section, create_fm=None):
    """Sync source content and source-derived metadata to destination."""
    with open(src_path, "r", encoding="utf-8") as f:
        src_content = f.read()

    src_body = extract_source_body(src_content)

    if os.path.exists(dst_path):
        with open(dst_path, "r", encoding="utf-8") as f:
            dst_content = f.read()
        fm, _ = extract_frontmatter(dst_content)
        if fm is None:
            print(f"  WARNING: No frontmatter in {dst_path}, skipping")
            return False
    else:
        if create_fm:
            fm = create_fm
        else:
            print(f"  WARNING: No frontmatter template for new file {dst_path}")
            return False

    fm = update_frontmatter_metadata(fm, source_mtime_date(src_path), section)
    new_content = f"---{fm}---\n{src_body}"

    if os.path.exists(dst_path) and dst_content == new_content:
        return False

    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True


def get_title_from_source(src_path):
    """Extract title from source file's first line."""
    with open(src_path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    # Remove leading tab if present
    if first_line.startswith("\t"):
        first_line = first_line[1:].strip()
    # Remove leading # and whitespace
    if first_line.startswith("# "):
        return first_line[2:].strip()
    elif first_line.startswith("#"):
        return first_line[1:].strip()
    return first_line


def get_description_from_source(src_path):
    """Extract description from source file (first blockquote line)."""
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Remove leading # title
    lines = content.split("\n")
    if lines and lines[0].startswith("\t"):
        lines[0] = lines[0][1:]
    if lines and lines[0].startswith("#"):
        lines = lines[1:]
    # Find first blockquote
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("> "):
            desc = stripped[2:].strip()
            # Truncate and clean
            if len(desc) > 150:
                desc = desc[:147] + "..."
            return desc
    return ""


def add_existing_destination(updates, category, num, src, dst, section):
    """Queue an existing mapped destination for idempotent synchronization."""
    if src and os.path.exists(dst):
        updates.append((category, num, src, dst, section, None))


def main():
    updates = []

    # 1. Main courses (00-32)
    for num in range(0, 33):
        src = find_source_file(SRC_DIR, num)
        dst = os.path.join(DST_DIR, f"course-{num:02d}.md")
        add_existing_destination(updates, "main", num, src, dst, "main")

    # 2. Math
    for num in [1]:
        src = find_source_file_numeric(os.path.join(SRC_DIR, "ai学习应用数学"), num)
        dst = os.path.join(DST_DIR, f"math-{num:02d}.md")
        add_existing_destination(updates, "math", num, src, dst, "supplement")

    # 3. Tools
    for num in [1, 2, 3]:
        src = find_source_file_numeric(os.path.join(SRC_DIR, "工具教学"), num)
        dst = os.path.join(DST_DIR, f"tools-{num:02d}.md")
        if src:
            if os.path.exists(dst):
                add_existing_destination(updates, "tools", num, src, dst, "supplement")
            else:
                # New file, need to create frontmatter
                title = get_title_from_source(src)
                desc = get_description_from_source(src)
                fm = f'\ntitle: "{title}"\npublished: 2026-01-01\nsection: supplement\ndescription: "{desc}"\ntags: ["AI 应用工程", "学习笔记"]\ncategory: "AI 应用工程"\ndraft: false\n'
                updates.append(("tools", num, src, dst, "supplement", fm))

    # 4. Language Schema (special: no number prefix)
    src = os.path.join(SRC_DIR, "编程语言基础", "Schema_声明式数据契约.md")
    dst = os.path.join(DST_DIR, "language-schema.md")
    add_existing_destination(updates, "lang", 0, src, dst, "supplement")

    # 5. Prerequisites
    prereq_dir = os.path.join(SRC_DIR, "新手需要学习的前置知识")
    for num in range(0, 28):
        src = find_source_file(prereq_dir, num)
        dst = os.path.join(DST_DIR, f"prereq-{num:02d}.md")
        add_existing_destination(updates, "prereq", num, src, dst, "prerequisite")

    print(f"Files to update: {len(updates)}")
    print("-" * 60)

    for category, num, src, dst, section, create_fm in updates:
        status = "NEW" if not os.path.exists(dst) else "UPD"
        print(f"[{status}] {os.path.basename(dst)} <- {os.path.basename(src)}")
        if sync_file(src, dst, section, create_fm):
            print(f"  ✓ Done")
        else:
            print(f"  ✗ Failed")

    print("-" * 60)
    print("Sync complete.")


if __name__ == "__main__":
    main()
