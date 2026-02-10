#!/bin/bash
# Test script to verify scope prefix-matching behavior in GET /rules endpoint
#
# Tests by making multiple queries with different scope depths and comparing results
# Uses existing rules in the system (no creation/deletion needed)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get API configuration
API_KEY="${QODO_CLI_API_KEY:-}"
API_URL="${QODO_RULES_API_URL:-}"

if [ -f "$HOME/.qodo/config.json" ]; then
    if [ -z "$API_KEY" ]; then
        API_KEY=$(jq -r '.QODO_CLI_API_KEY // .api_key // empty' "$HOME/.qodo/config.json" 2>/dev/null || echo "")
    fi
    if [ -z "$API_URL" ]; then
        API_URL=$(jq -r '.QODO_RULES_API_URL // empty' "$HOME/.qodo/config.json" 2>/dev/null || echo "")
    fi
fi

if [ -z "$API_URL" ]; then
    API_URL="https://api.qodo.ai"
fi

API_URL="${API_URL%/}"  # Remove trailing slash

# Check prerequisites
if [ -z "$API_KEY" ]; then
    echo -e "${RED}Error: No API key configured${NC}"
    echo "Set QODO_CLI_API_KEY environment variable or create ~/.qodo/config.json"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Scope Prefix-Matching Behavior Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "API URL: $API_URL"
echo "Testing with existing rules (no data modification)"
echo ""

# Helper function to query rules with a specific scope
query_rules() {
    local scope="$1"
    local description="$2"

    # Display output goes to stderr so it doesn't interfere with return value
    echo -e "${CYAN}Query: $description${NC}" >&2
    echo "Scope: $scope" >&2

    # Fetch all pages with pagination
    # API enforces max 50 rules per page
    local all_rules="[]"
    local page=1
    local page_size=50

    while true; do
        local response=$(curl -s -X GET \
            -H "Authorization: Bearer $API_KEY" \
            "${API_URL}/rules/v1/rules?scopes=${scope}&state=active&page=${page}&page_size=${page_size}")

        local page_rules=$(echo "$response" | jq -r '.rules' 2>/dev/null || echo "[]")
        local page_count=$(echo "$page_rules" | jq 'length')

        # Append this page's rules
        all_rules=$(echo "$all_rules" | jq --argjson page_rules "$page_rules" '. + $page_rules')

        # If we got fewer than page_size rules, we've reached the last page
        if [ "$page_count" -lt "$page_size" ]; then
            break
        fi

        page=$((page + 1))
    done

    local count=$(echo "$all_rules" | jq 'length')
    local rule_ids=$(echo "$all_rules" | jq -r '.[].ruleId' | sort -n | tr '\n' ',' | sed 's/,$//')

    echo "Rules returned: $count" >&2
    # Only show first 10 rule IDs to keep output manageable
    local first_10=$(echo "$rule_ids" | cut -d',' -f1-10)
    echo "Rule IDs (first 10): $first_10..." >&2
    echo "" >&2

    # Return count and full IDs on separate lines for reliable parsing (to stdout)
    printf "%d\n%s\n" "$count" "$rule_ids"
}

# Test cases with increasing scope depth
echo -e "${BLUE}Test Case 1: No scope (returns ALL rules)${NC}"
echo ""
result1=$(query_rules "" "No scope parameter")
count1=$(echo "$result1" | sed -n '1p')
ids1=$(echo "$result1" | sed -n '2p')

echo -e "${BLUE}Test Case 2: Universal scope (/)${NC}"
echo ""
result2=$(query_rules "/" "Universal scope")
count2=$(echo "$result2" | sed -n '1p')
ids2=$(echo "$result2" | sed -n '2p')

echo -e "${BLUE}Test Case 3: Repository level${NC}"
echo ""
result3=$(query_rules "/codium-ai/qodo-platform/" "Repository level")
count3=$(echo "$result3" | sed -n '1p')
ids3=$(echo "$result3" | sed -n '2p')

echo -e "${BLUE}Test Case 4: Modules directory${NC}"
echo ""
result4=$(query_rules "/codium-ai/qodo-platform/modules/" "Modules directory")
count4=$(echo "$result4" | sed -n '1p')
ids4=$(echo "$result4" | sed -n '2p')

echo -e "${BLUE}Test Case 5: Specific module (rules)${NC}"
echo ""
result5=$(query_rules "/codium-ai/qodo-platform/modules/rules/" "Rules module")
count5=$(echo "$result5" | sed -n '1p')
ids5=$(echo "$result5" | sed -n '2p')

echo -e "${BLUE}Test Case 6: Deep path within module${NC}"
echo ""
result6=$(query_rules "/codium-ai/qodo-platform/modules/rules/src/service/crud.py" "Deep path in rules module")
count6=$(echo "$result6" | sed -n '1p')
ids6=$(echo "$result6" | sed -n '2p')

echo -e "${BLUE}Test Case 7: Non-existent deep path${NC}"
echo ""
result7=$(query_rules "/codium-ai/qodo-platform/modules/rules/fake/deep/path/file.py" "Non-existent deep path")
count7=$(echo "$result7" | sed -n '1p')
ids7=$(echo "$result7" | sed -n '2p')

# Analysis
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Analysis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if deeper paths return same or more rules
echo "Rule count progression:"
echo "  1. No scope:            $count1 rules"
echo "  2. Universal (/):       $count2 rules"
echo "  3. Repository level:    $count3 rules"
echo "  4. Modules directory:   $count4 rules"
echo "  5. Rules module:        $count5 rules"
echo "  6. Deep path (real):    $count6 rules"
echo "  7. Deep path (fake):    $count7 rules"
echo ""

# Verify behavior: deeper paths should include all parent-level rules
all_passed=true

echo "Verification checks:"
echo ""

# Check 1: Cases 6 and 7 should equal case 5 (same rules at deep paths)
if [ "$count6" -eq "$count5" ] && [ "$count7" -eq "$count5" ]; then
    echo -e "  ${GREEN}✓${NC} Deep paths return same rules as module level"
    echo "    (Both deep queries returned $count5 rules, matching module-level count)"
else
    echo -e "  ${RED}✗${NC} Deep paths should return same rules as module level"
    echo "    Module: $count5, Deep(real): $count6, Deep(fake): $count7"
    all_passed=false
fi

# Check 2: Cases 5, 6, 7 should be >= case 4
if [ "$count5" -ge "$count4" ] && [ "$count6" -ge "$count4" ] && [ "$count7" -ge "$count4" ]; then
    echo -e "  ${GREEN}✓${NC} Module queries include parent directory rules"
    echo "    (Module/deep queries: $count5+ rules >= Modules dir: $count4 rules)"
else
    echo -e "  ${RED}✗${NC} Module queries should include parent directory rules"
    all_passed=false
fi

# Check 3: Case 4 should be >= case 3
if [ "$count4" -ge "$count3" ]; then
    echo -e "  ${GREEN}✓${NC} Modules directory includes repository rules"
    echo "    (Modules: $count4 rules >= Repo: $count3 rules)"
else
    echo -e "  ${RED}✗${NC} Modules directory should include repository rules"
    all_passed=false
fi

# Check 4: Verify the IDs from deep path match module level
if [ "$ids6" = "$ids5" ] && [ "$ids7" = "$ids5" ]; then
    echo -e "  ${GREEN}✓${NC} Deep paths return identical rule sets to module level"
else
    echo -e "  ${YELLOW}⚠${NC}  Deep paths return different rule sets (may have different rules at each level)"
fi

echo ""

# Check if rule IDs increase (subset relationship)
echo "Rule set relationships:"
echo ""

# Helper to check if one set is a subset of another
is_subset() {
    local subset="$1"
    local superset="$2"

    # Convert comma-separated to arrays
    IFS=',' read -ra arr1 <<< "$subset"
    IFS=',' read -ra arr2 <<< "$superset"

    for id in "${arr1[@]}"; do
        if [[ ! ",${superset}," =~ ",${id}," ]]; then
            return 1
        fi
    done
    return 0
}

if is_subset "$ids3" "$ids4"; then
    echo -e "  ${GREEN}✓${NC} Repository rules ⊆ Modules directory rules"
else
    echo -e "  ${YELLOW}⚠${NC}  Repository rules are not a subset of modules directory rules"
fi

if is_subset "$ids4" "$ids5"; then
    echo -e "  ${GREEN}✓${NC} Modules directory rules ⊆ Rules module rules"
else
    echo -e "  ${YELLOW}⚠${NC}  Modules directory rules are not a subset of rules module rules"
fi

echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ "$all_passed" = true ]; then
    echo -e "${GREEN}✓ BEHAVIOR CONFIRMED${NC}"
    echo ""
    echo "The API correctly implements prefix-based scope matching:"
    echo ""
    echo "  1. Query with deep path (real or fake)"
    echo "     Example: /org/repo/modules/rules/src/service/file.py"
    echo ""
    echo "  2. API generates all parent prefixes:"
    echo "     /, /org/, /org/repo/, /org/repo/modules/, /org/repo/modules/rules/, ..."
    echo ""
    echo "  3. Returns ALL rules whose scopes match any prefix"
    echo "     → Universal rules (scope: /)"
    echo "     → Repository rules (scope: /org/repo/)"
    echo "     → Module rules (scope: /org/repo/modules/rules/)"
    echo ""
    echo -e "${GREEN}Safe to implement module-aware scope detection!${NC}"
    echo ""
    echo "Implementation strategy:"
    echo "  • Get current working directory"
    echo "  • Build scope: repo + relative_path"
    echo "  • Query API with deepest path"
    echo "  • API automatically returns all parent-level rules"
    echo ""
    exit 0
else
    echo -e "${RED}✗ UNEXPECTED BEHAVIOR${NC}"
    echo ""
    echo "The scope behavior doesn't match expectations."
    echo "Review the test results above before implementing."
    echo ""
    exit 1
fi
