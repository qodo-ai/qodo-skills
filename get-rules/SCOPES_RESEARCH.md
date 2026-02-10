# Scopes Parameter Research - Qodo Rules API

Research findings for extending the get-rules skill to support module-level scope identification.

---

## How Scopes Work

### Hierarchical Path Format

Scopes follow a hierarchical directory-like structure with leading and trailing slashes:

```
/                                    # Universal (matches everything)
/org/                                # Organization level
/org/repo/                           # Repository level
/org/repo/modules/                   # Path level
/org/repo/modules/rules/             # Deep path (module-specific)
```

### Prefix-Based Matching

**Rules are matched using prefix logic** - a rule's scope matches if it's a prefix of the query path:

**Example:** Query for `/Codium-ai/qodo-platform/modules/rules/src/service.py` returns rules with scopes:
- `/` (universal - matches all)
- `/Codium-ai/` (org-level)
- `/Codium-ai/qodo-platform/` (repo-level)
- `/Codium-ai/qodo-platform/modules/` (path-level)
- `/Codium-ai/qodo-platform/modules/rules/` (module-specific)

### Key Properties

1. **No Partial Matching**: `/src/` does NOT match `/srcOther/`
2. **Automatic Normalization**:
   - Leading slash added if missing
   - Trailing slash added if missing
   - Duplicates removed
   - Empty/null defaults to `/` (universal)

3. **Multiple Scopes per Rule**:
   - Each rule can have up to 25 scopes
   - A rule matches if ANY of its scopes is a prefix of the query path

4. **API Query Format**:
   ```
   GET /rules/v1/rules?scopes=/org/repo/path/&state=active
   ```

---

## Current Implementation

### fetch-qodo-rules.sh Script

Currently extracts **repository scope only**:

```bash
# Current: git@github.com:Codium-ai/qodo-platform.git → /Codium-ai/qodo-platform/
REPO_SCOPE=$(echo "$REMOTE_URL" | sed -E 's|^.*[:/]([^/]+/[^/]+)\.git$|/\1/|')

# API Call
curl "https://${API_URL}/rules/v1/rules?scopes=${REPO_SCOPE}&state=active"
```

**Result**: Fetches repository-level + universal rules only.

---

## Proposed Enhancement: Module-Aware Scopes

### Goal

When working in a specific module directory (e.g., `modules/rules/`), fetch:
1. **Universal rules** (`/`)
2. **Repository-level rules** (`/Codium-ai/qodo-platform/`)
3. **Module-specific rules** (`/Codium-ai/qodo-platform/modules/rules/`)

### Implementation Strategy

#### 1. Detect Current Module

```bash
# Get current working directory relative to repo root
REPO_ROOT=$(git rev-parse --show-toplevel)
CWD=$(pwd)
REL_PATH=${CWD#$REPO_ROOT/}  # Remove repo root prefix

# Check if we're in a module directory
if [[ "$REL_PATH" == modules/* ]]; then
    # Extract module name: modules/rules/src/service.py → modules/rules
    MODULE_PATH=$(echo "$REL_PATH" | sed -E 's|(modules/[^/]+).*|\1|')

    # Construct module scope
    MODULE_SCOPE="${REPO_SCOPE}${MODULE_PATH}/"
    # Example: /Codium-ai/qodo-platform/modules/rules/
fi
```

#### 2. Build Scope Query

**Option A: Multiple Scope Values (Recommended)**
```bash
if [ -n "$MODULE_SCOPE" ]; then
    # Pass both repo and module scopes
    SCOPES_PARAM="scopes=${REPO_SCOPE}&scopes=${MODULE_SCOPE}"
else
    # Just repo scope
    SCOPES_PARAM="scopes=${REPO_SCOPE}"
fi

curl "${API_URL}/rules/v1/rules?${SCOPES_PARAM}&state=active"
```

**Option B: Single Deep Path Scope**
```bash
# Use the most specific scope (deepest path)
# API will automatically return all parent scopes due to prefix matching
QUERY_SCOPE="${MODULE_SCOPE:-$REPO_SCOPE}"
curl "${API_URL}/rules/v1/rules?scopes=${QUERY_SCOPE}&state=active"
```

**Recommendation**: Use Option B - query with the deepest scope path. The API's prefix matching will automatically include all parent-level rules.

#### 3. Output Formatting

Update the script output to show scope context:

```bash
if [ -n "$MODULE_SCOPE" ]; then
    echo "# 📋 Qodo Rules Loaded"
    echo ""
    echo "Repository: \`$REPO_SCOPE\`"
    echo "Module: \`$MODULE_PATH\`"
    echo "Scope: \`$MODULE_SCOPE\`"
else
    echo "# 📋 Qodo Rules Loaded"
    echo ""
    echo "Repository: \`$REPO_SCOPE\`"
    echo "Scope: Repository-wide"
fi
```

---

## Test Cases

### Case 1: Working in Repository Root
```bash
$ pwd
/Users/user/Projects/qodo-platform

Expected behavior:
- Scope: /Codium-ai/qodo-platform/
- Fetches: Universal + Repo-level rules
```

### Case 2: Working in Module Directory
```bash
$ pwd
/Users/user/Projects/qodo-platform/modules/rules

Expected behavior:
- Scope: /Codium-ai/qodo-platform/modules/rules/
- Fetches: Universal + Repo-level + Module-specific rules
```

### Case 3: Working in Deep Module Path
```bash
$ pwd
/Users/user/Projects/qodo-platform/modules/rules/src/service

Expected behavior:
- Scope: /Codium-ai/qodo-platform/modules/rules/
- Fetches: Universal + Repo-level + Module-specific rules
- Note: Trims to module root (modules/rules/), not deep path
```

### Case 4: Working Outside Modules
```bash
$ pwd
/Users/user/Projects/qodo-platform/docs

Expected behavior:
- Scope: /Codium-ai/qodo-platform/
- Fetches: Universal + Repo-level rules (no module-specific)
```

---

## Implementation Checklist

- [ ] Add module detection logic to fetch-qodo-rules.sh
- [ ] Extract module path from working directory
- [ ] Construct module scope string
- [ ] Update API query to use deepest applicable scope
- [ ] Update output formatting to show scope context
- [ ] Test all four cases above
- [ ] Update skill.md documentation
- [ ] Add SCOPES_RESEARCH.md to skill documentation

---

## API Reference

### Scope Query Parameter

**Endpoint**: `GET /rules/v1/rules`

**Query Parameter**: `scopes` (repeatable)
```
?scopes=/org/repo/&scopes=/org/repo/modules/rules/
```

**Filtering Logic**: Returns rules where ANY rule scope is a prefix of ANY query scope.

**Example API Response**:
```json
{
  "rules": [
    {
      "id": 123,
      "name": "Use snake_case for Python variables",
      "scopes": ["/Codium-ai/qodo-platform/"],
      "severity": "warning"
    },
    {
      "id": 456,
      "name": "Repository pattern for all data access",
      "scopes": ["/Codium-ai/qodo-platform/modules/rules/"],
      "severity": "error"
    }
  ],
  "totalCount": 2
}
```

---

## References

- Test file: `tests/integration/modules/rules/test_scope_filtering.py`
- Migration: `modules/rules/src/migrations/alembic/versions/2026_01_14_1200_migrate_scope_to_scopes_array.py`
- Model: `modules/rules/src/model.py` (lines 71-77)

---

**Version:** 1.0
**Date:** 2026-02-10
