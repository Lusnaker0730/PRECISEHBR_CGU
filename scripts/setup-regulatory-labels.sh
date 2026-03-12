#!/bin/bash
# Setup GitHub labels for IEC 62304 / ISO 14971 regulatory traceability
# Usage: ./scripts/setup-regulatory-labels.sh

set -e

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "Setting up regulatory labels for: $REPO"

# IEC 62304 labels
gh label create "requirement"    --description "IEC 62304 - Software Requirement (SRS)" --color "0075ca" --force
gh label create "design"         --description "IEC 62304 - Software Design (SDS)" --color "5319e7" --force
gh label create "risk"           --description "ISO 14971 - Risk Analysis" --color "d93f0b" --force
gh label create "test"           --description "IEC 62304 - Test Case (V&V)" --color "0e8a16" --force
gh label create "verification"   --description "IEC 62304 - Verification activity" --color "006b75" --force
gh label create "IEC-62304"      --description "IEC 62304 Software Lifecycle" --color "fbca04" --force
gh label create "ISO-14971"      --description "ISO 14971 Risk Management" --color "e4e669" --force

# Safety classification
gh label create "class-A"        --description "IEC 62304 Class A - No injury" --color "c5def5" --force
gh label create "class-B"        --description "IEC 62304 Class B - Non-serious injury" --color "f9d0c4" --force
gh label create "class-C"        --description "IEC 62304 Class C - Serious injury/death" --color "d93f0b" --force

# Change control
gh label create "change-control"  --description "Design change requiring review" --color "bfd4f2" --force
gh label create "CAPA"           --description "Corrective/Preventive Action" --color "b60205" --force

echo "Done! Labels created for regulatory traceability."
