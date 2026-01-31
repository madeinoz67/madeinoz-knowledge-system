#!/usr/bin/env python3
"""
Validation script for cliff.toml configuration changes.
Tests that all required fixes are properly configured.
"""
import sys
import tomllib
from pathlib import Path

def validate_cliff_config():
    """Validate cliff.toml has all required configurations"""
    errors = []
    warnings = []
    
    # Load cliff.toml
    cliff_path = Path(__file__).parent.parent / "cliff.toml"
    with open(cliff_path, 'rb') as f:
        config = tomllib.load(f)
    
    git_config = config.get('git', {})
    
    # P0: Check protect_breaking_commits
    if not git_config.get('protect_breaking_commits', False):
        errors.append("❌ P0: protect_breaking_commits must be true")
    else:
        print("✅ P0: protect_breaking_commits = true")
    
    # P0: Check breaking change parsers exist
    commit_parsers = git_config.get('commit_parsers', [])
    has_breaking_message = False
    has_breaking_footer = False
    has_breaking_footer_alt = False
    
    for parser in commit_parsers:
        if parser.get('message') == '^[a-z]+!:' and parser.get('group') == '⚠ BREAKING CHANGES':
            has_breaking_message = True
        if parser.get('footer') == '^BREAKING CHANGE:' and parser.get('group') == '⚠ BREAKING CHANGES':
            has_breaking_footer = True
        if parser.get('footer') == '^BREAKING-CHANGE:' and parser.get('group') == '⚠ BREAKING CHANGES':
            has_breaking_footer_alt = True
    
    if not has_breaking_message:
        errors.append("❌ P0: Missing breaking change parser for ^[a-z]+!: pattern")
    else:
        print("✅ P0: Breaking change parser for !: suffix exists")
    
    if not has_breaking_footer:
        errors.append("❌ P0: Missing breaking change parser for BREAKING CHANGE: footer")
    else:
        print("✅ P0: Breaking change parser for BREAKING CHANGE: footer exists")
    
    if not has_breaking_footer_alt:
        warnings.append("⚠️  P0: Missing breaking change parser for BREAKING-CHANGE: footer")
    else:
        print("✅ P0: Breaking change parser for BREAKING-CHANGE: footer exists")
    
    # P1: Check GitHub keywords preprocessor
    preprocessors = git_config.get('commit_preprocessors', [])
    has_github_keywords = False
    
    for preprocessor in preprocessors:
        pattern = preprocessor.get('pattern', '')
        if 'closes|fixes|resolves' in pattern.lower():
            has_github_keywords = True
            break
    
    if not has_github_keywords:
        errors.append("❌ P1: Missing GitHub keywords preprocessor (Closes/Fixes/Resolves #123)")
    else:
        print("✅ P1: GitHub keywords preprocessor exists")
    
    # P2: Check GitHub remote integration
    remote = config.get('remote', {})
    github = remote.get('github', {})
    
    if not github.get('owner') or not github.get('repo'):
        warnings.append("⚠️  P2: GitHub remote integration incomplete")
    else:
        print(f"✅ P2: GitHub remote integration configured ({github['owner']}/{github['repo']})")
    
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
        print("\n🎉 All configuration checks passed!")
    elif not errors:
        print("\n✅ All critical checks passed (warnings can be addressed later)")
    
    return len(errors) == 0

if __name__ == "__main__":
    success = validate_cliff_config()
    sys.exit(0 if success else 1)
