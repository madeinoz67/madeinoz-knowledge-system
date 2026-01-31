#!/usr/bin/env python3
"""
Validation script for CI workflow configuration changes.
Tests that concurrency control is properly configured.
"""
import sys
import yaml
from pathlib import Path

def validate_ci_workflow():
    """Validate .github/workflows/ci.yml has all required configurations"""
    errors = []
    warnings = []
    
    # Load ci.yml
    ci_path = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
    with open(ci_path) as f:
        config = yaml.safe_load(f)
    
    jobs = config.get('jobs', {})
    
    # P1: Check release job concurrency
    release = jobs.get('release', {})
    release_concurrency = release.get('concurrency', {})
    
    if not release_concurrency:
        errors.append("❌ P1: Missing concurrency control in release job")
    else:
        group = release_concurrency.get('group')
        cancel = release_concurrency.get('cancel-in-progress')
        
        if group != 'changelog-update':
            errors.append(f"❌ P1: Release concurrency group should be 'changelog-update', got '{group}'")
        elif cancel is not False:
            errors.append(f"❌ P1: Release cancel-in-progress should be false, got {cancel}")
        else:
            print("✅ P1: Release job concurrency control properly configured")
    
    # P1: Check update-unreleased job concurrency
    update = jobs.get('update-unreleased', {})
    update_concurrency = update.get('concurrency', {})
    
    if not update_concurrency:
        errors.append("❌ P1: Missing concurrency control in update-unreleased job")
    else:
        group = update_concurrency.get('group')
        cancel = update_concurrency.get('cancel-in-progress')
        
        if group != 'changelog-update':
            errors.append(f"❌ P1: Update-unreleased concurrency group should be 'changelog-update', got '{group}'")
        elif cancel is not False:
            errors.append(f"❌ P1: Update-unreleased cancel-in-progress should be false, got {cancel}")
        else:
            print("✅ P1: Update-unreleased job concurrency control properly configured")
    
    # Verify both use the same concurrency group
    if release_concurrency.get('group') == update_concurrency.get('group') == 'changelog-update':
        print("✅ P1: Both jobs use the same concurrency group (prevents race conditions)")
    else:
        warnings.append("⚠️  P1: Concurrency groups don't match between jobs")
    
    # Print results
    print("\n" + "="*60)
    if errors:
        print(f"\n🚨 {len(errors)} ERRORS FOUND:\n")
        for error in errors:
            print(f"  {error}")
    
    if warnings:
        print(f"\n⚠️  {len(warnings)} WARNINGS:\n")
        for warning in warnings:
            print(f"  {warning}")
    
    if not errors and not warnings:
        print("\n🎉 All CI workflow checks passed!")
    elif not errors:
        print("\n✅ All critical checks passed (warnings can be addressed later)")
    
    return len(errors) == 0

if __name__ == "__main__":
    success = validate_ci_workflow()
    sys.exit(0 if success else 1)
