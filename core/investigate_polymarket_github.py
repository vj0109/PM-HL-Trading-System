#!/usr/bin/env python3
"""
INVESTIGATE OFFICIAL POLYMARKET GITHUB REPOSITORIES
Find the correct API endpoints from official sources
"""

import requests
import json
import time
from typing import Dict, List

class PolymarketGitHubInvestigator:
    def __init__(self):
        self.github_api = "https://api.github.com"
        self.polymarket_org = "Polymarket"
    
    def get_polymarket_repositories(self) -> List[Dict]:
        """Get all Polymarket repositories"""
        print("🔍 FETCHING ALL POLYMARKET REPOSITORIES")
        print("=" * 50)
        
        try:
            url = f"{self.github_api}/orgs/{self.polymarket_org}/repos"
            params = {
                'type': 'all',
                'per_page': 100,
                'sort': 'updated'
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            repos = response.json()
            print(f"📊 Found {len(repos)} repositories")
            
            # Sort by relevance for API investigation
            api_keywords = ['api', 'sdk', 'client', 'docs', 'data', 'activity', 'trade', 'price', 'history']
            
            scored_repos = []
            for repo in repos:
                name = repo['name'].lower()
                description = (repo.get('description') or '').lower()
                
                # Score based on API-relevant keywords
                score = 0
                for keyword in api_keywords:
                    if keyword in name:
                        score += 3
                    if keyword in description:
                        score += 1
                
                scored_repos.append({
                    'repo': repo,
                    'score': score
                })
            
            # Sort by score (most relevant first)
            scored_repos.sort(key=lambda x: x['score'], reverse=True)
            
            return [item['repo'] for item in scored_repos]
            
        except Exception as e:
            print(f"❌ Error fetching repositories: {e}")
            return []
    
    def analyze_repository_for_apis(self, repo: Dict) -> Dict:
        """Analyze a repository for API endpoints and documentation"""
        name = repo['name']
        print(f"\n🔍 ANALYZING: {name}")
        print("-" * 40)
        
        analysis = {
            'name': name,
            'description': repo.get('description', ''),
            'language': repo.get('language', ''),
            'updated': repo.get('updated_at', ''),
            'api_endpoints': [],
            'config_files': [],
            'documentation': [],
            'examples': []
        }
        
        try:
            # Get repository contents
            contents_url = repo['contents_url'].replace('{+path}', '')
            response = requests.get(contents_url, timeout=10)
            
            if response.status_code != 200:
                print(f"   ❌ Cannot access contents")
                return analysis
                
            contents = response.json()
            
            # Look for relevant files
            relevant_files = []
            for item in contents:
                name_lower = item['name'].lower()
                
                if any(keyword in name_lower for keyword in ['api', 'endpoint', 'url', 'config', 'const']):
                    relevant_files.append(item)
                elif item['name'].endswith(('.md', '.py', '.js', '.ts', '.json')):
                    relevant_files.append(item)
            
            # Download and analyze relevant files
            for file_item in relevant_files[:10]:  # Limit to first 10 files
                file_analysis = self.analyze_file(file_item)
                if file_analysis:
                    for key in ['api_endpoints', 'config_files', 'documentation', 'examples']:
                        analysis[key].extend(file_analysis.get(key, []))
            
            # Print summary
            print(f"   📊 Description: {analysis['description']}")
            print(f"   🔧 Language: {analysis['language']}")
            print(f"   📅 Updated: {analysis['updated']}")
            
            if analysis['api_endpoints']:
                print(f"   🎯 API Endpoints Found: {len(analysis['api_endpoints'])}")
                for endpoint in analysis['api_endpoints'][:3]:
                    print(f"      - {endpoint}")
                    
            if analysis['documentation']:
                print(f"   📚 Documentation: {len(analysis['documentation'])} files")
                
        except Exception as e:
            print(f"   ❌ Error analyzing repository: {e}")
        
        return analysis
    
    def analyze_file(self, file_item: Dict) -> Dict:
        """Analyze a specific file for API information"""
        file_name = file_item['name']
        download_url = file_item.get('download_url')
        
        if not download_url:
            return {}
        
        try:
            response = requests.get(download_url, timeout=5)
            if response.status_code != 200:
                return {}
                
            content = response.text
            analysis = {
                'api_endpoints': [],
                'config_files': [],
                'documentation': [],
                'examples': []
            }
            
            # Look for API endpoints in content
            api_patterns = [
                'gamma-api.polymarket.com',
                'clob.polymarket.com',
                'api.polymarket.com',
                '/activity',
                '/prices-history',
                '/trades',
                '/markets',
                '/events'
            ]
            
            content_lower = content.lower()
            for pattern in api_patterns:
                if pattern in content_lower:
                    # Extract lines containing the pattern
                    lines = content.split('\n')
                    for line in lines:
                        if pattern.lower() in line.lower():
                            analysis['api_endpoints'].append(f"{file_name}: {line.strip()}")
            
            # Check if this is documentation
            if file_name.lower().endswith('.md'):
                analysis['documentation'].append(f"{file_name}: {len(content)} chars")
                
            # Check if this is a config file
            if any(word in file_name.lower() for word in ['config', 'const', 'env']):
                analysis['config_files'].append(f"{file_name}: {len(content)} chars")
            
            return analysis
            
        except Exception as e:
            return {}
    
    def find_python_sdk(self, repos: List[Dict]) -> Dict:
        """Look specifically for Python SDK"""
        print(f"\n🐍 LOOKING FOR PYTHON SDK")
        print("=" * 30)
        
        python_repos = [r for r in repos if r.get('language') == 'Python']
        
        for repo in python_repos[:5]:
            name = repo['name']
            print(f"📦 {name}: {repo.get('description', '')}")
            
            # This looks like the main Python client
            if 'python' in name.lower() or 'client' in name.lower():
                analysis = self.analyze_repository_for_apis(repo)
                if analysis['api_endpoints']:
                    return analysis
        
        return {}
    
    def find_api_documentation(self, repos: List[Dict]) -> List[Dict]:
        """Look for API documentation repositories"""
        print(f"\n📚 LOOKING FOR API DOCUMENTATION")
        print("=" * 35)
        
        doc_repos = []
        for repo in repos:
            name = repo['name'].lower()
            desc = (repo.get('description') or '').lower()
            
            if any(word in name or word in desc for word in ['api', 'docs', 'documentation', 'sdk']):
                doc_repos.append(repo)
        
        analyses = []
        for repo in doc_repos[:5]:
            analysis = self.analyze_repository_for_apis(repo)
            analyses.append(analysis)
            
        return analyses

def main():
    """Investigate Polymarket GitHub repositories for API endpoints"""
    investigator = PolymarketGitHubInvestigator()
    
    print("🚀 INVESTIGATING OFFICIAL POLYMARKET GITHUB REPOSITORIES")
    print("📊 Looking for correct API endpoints from official sources")
    print("🔗 https://github.com/orgs/Polymarket/repositories")
    print("=" * 80)
    
    # Get all repositories
    repos = investigator.get_polymarket_repositories()
    
    if not repos:
        print("❌ Failed to fetch repositories")
        return
    
    print(f"\n📊 TOP 10 MOST RELEVANT REPOSITORIES:")
    print("=" * 50)
    
    for i, repo in enumerate(repos[:10]):
        name = repo['name']
        desc = repo.get('description', 'No description')
        lang = repo.get('language', 'Unknown')
        stars = repo.get('stargazers_count', 0)
        
        print(f"{i+1:2d}. {name:<25} | {lang:<10} | ⭐ {stars:<3} | {desc}")
    
    # Look specifically for Python SDK
    python_analysis = investigator.find_python_sdk(repos)
    
    # Look for API documentation
    doc_analyses = investigator.find_api_documentation(repos)
    
    # Analyze top 5 most relevant repositories in detail
    print(f"\n🔍 DETAILED ANALYSIS OF TOP 5 REPOSITORIES")
    print("=" * 55)
    
    detailed_results = []
    for repo in repos[:5]:
        analysis = investigator.analyze_repository_for_apis(repo)
        detailed_results.append(analysis)
        time.sleep(1)  # Rate limiting
    
    # Summary
    print(f"\n📊 INVESTIGATION SUMMARY")
    print("=" * 30)
    
    all_endpoints = []
    for analysis in detailed_results:
        all_endpoints.extend(analysis['api_endpoints'])
    
    if all_endpoints:
        print(f"✅ Found {len(all_endpoints)} potential API endpoints:")
        for endpoint in all_endpoints[:10]:
            print(f"   {endpoint}")
    else:
        print("❌ No API endpoints found in top repositories")
    
    print(f"\n🎯 NEXT STEPS:")
    print("1. Check the most promising repositories manually")
    print("2. Look for official API documentation")
    print("3. Test endpoints found in the code")
    print("4. Consider contacting Polymarket if endpoints are not public")

if __name__ == "__main__":
    main()