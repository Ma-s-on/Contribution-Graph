#!/usr/bin/env python3
"""
GitHub Contribution Graph Image Generator

A Python tool to draw images on your GitHub contribution graph by creating
commits with custom dates. Enhanced with text generation, templates, and better visuals.

Usage:
    python contribution.py preview -img image.png
    python contribution.py preview -text "HIRE ME"
    python contribution.py push -img image.png -repo username/repo
    python contribution.py push -template skull -repo username/repo
    python contribution.py list-templates
"""

import argparse
import os
import sys
import subprocess
import shutil
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import tempfile
import json
import webbrowser
import requests
import logging
import keyring

try:
    import colorama
    colorama.init()
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

GITHUB_KEYRING_SERVICE = 'github_contribution_generator_pat'
GITHUB_PAT = None  # Global variable to store PAT for the session

# Dependency check
REQUIRED_PACKAGES = [
    ("numpy", "numpy"),
    ("PIL", "Pillow"),
    ("requests", "requests"),
    ("colorama", "colorama"),
    ("keyring", "keyring")
]
missing = []
for mod, pip_name in REQUIRED_PACKAGES:
    try:
        __import__(mod)
    except ImportError:
        missing.append(pip_name)
if missing:
    print("\nMissing required packages:")
    for pkg in missing:
        print(f"  - {pkg}")
    print(f"\nPlease install them with:\n  pip install {' '.join(missing)}\n")
    sys.exit(1)

# Error logging
logging.basicConfig(filename='github_contribution_generator.log',
                    level=logging.ERROR,
                    format='%(asctime)s %(levelname)s %(message)s')

def log_uncaught_exceptions(exctype, value, tb):
    import traceback
    logging.error("Uncaught exception:", exc_info=(exctype, value, tb))
    print("\nAn unexpected error occurred. Details have been logged to github_contribution_generator.log.\n")
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = log_uncaught_exceptions

class ContributionGenerator:
    def __init__(self):
        self.GITHUB_WEEKS = 52
        self.GITHUB_DAYS = 7
        self.MAX_INTENSITY = 4  # GitHub shows 0-4 intensity levels
        
        # GitHub's actual contribution colors for better preview
        self.GITHUB_COLORS = {
            0: '\033[48;2;22;27;34m  \033[0m',      # Dark gray
            1: '\033[48;2;14;68;41m  \033[0m',      # Light green
            2: '\033[48;2;0;109;50m  \033[0m',      # Medium green
            3: '\033[48;2;38;166;65m  \033[0m',     # Bright green
            4: '\033[48;2;57;211;83m  \033[0m'      # Brightest green
        }
        
        if sys.platform == 'win32' and COLORAMA_AVAILABLE:
            from colorama import Back, Style
            self.GITHUB_COLORS = {
                0: Back.BLACK + '  ' + Style.RESET_ALL,
                1: Back.GREEN + '  ' + Style.RESET_ALL,
                2: Back.LIGHTGREEN_EX + '  ' + Style.RESET_ALL,
                3: Back.YELLOW + '  ' + Style.RESET_ALL,
                4: Back.WHITE + '  ' + Style.RESET_ALL
            }
        
        self.templates = self._load_templates()
    
    def _load_templates(self):
        """Load built-in templates"""
        return {
            "skull": [
                [0,0,2,2,2,2,0,0],
                [0,2,4,2,2,4,2,0],
                [2,4,4,2,2,4,4,2],
                [2,2,2,4,4,2,2,2],
                [2,4,2,2,2,2,4,2],
                [0,2,4,4,4,4,2,0],
                [0,0,2,2,2,2,0,0]
            ],
            "heart": [
                [0,2,2,0,2,2,0],
                [2,4,4,2,4,4,2],
                [4,4,4,4,4,4,4],
                [4,4,4,4,4,4,4],
                [2,4,4,4,4,4,2],
                [0,2,4,4,4,2,0],
                [0,0,2,2,2,0,0]
            ],
            "smile": [
                [0,0,2,2,2,2,0,0],
                [0,2,0,2,2,0,2,0],
                [2,0,4,0,0,4,0,2],
                [2,0,0,0,0,0,0,2],
                [2,0,4,0,0,4,0,2],
                [2,0,0,4,4,0,0,2],
                [0,2,0,0,0,0,2,0],
                [0,0,2,2,2,2,0,0]
            ],
            "diamond": [
                [0,0,0,2,0,0,0],
                [0,0,2,4,2,0,0],
                [0,2,4,4,4,2,0],
                [2,4,4,4,4,4,2],
                [0,2,4,4,4,2,0],
                [0,0,2,4,2,0,0],
                [0,0,0,2,0,0,0]
            ],
            "checkmark": [
                [0,0,0,0,0,0,2],
                [0,0,0,0,0,2,4],
                [0,0,0,0,2,4,2],
                [2,0,0,2,4,2,0],
                [4,2,2,4,2,0,0],
                [2,4,4,2,0,0,0],
                [0,2,2,0,0,0,0]
            ]
        }
    
    def list_templates(self):
        """List available templates with previews"""
        print("Available templates:\n")
        
        for name, pattern in self.templates.items():
            print(f"🎨 {name.upper()}:")
            # Convert to numpy array and pad to show properly  
            template_array = np.array(pattern)
            if template_array.shape[0] < self.GITHUB_DAYS:
                # Pad with zeros to fit 7 days
                pad_height = self.GITHUB_DAYS - template_array.shape[0]
                template_array = np.pad(template_array, ((0, pad_height), (0, 0)), 'constant')
            
            # Resize to fit contribution graph if needed
            if template_array.shape[1] > self.GITHUB_WEEKS:
                template_array = template_array[:, :self.GITHUB_WEEKS]
            elif template_array.shape[1] < self.GITHUB_WEEKS:
                pad_width = self.GITHUB_WEEKS - template_array.shape[1]
                template_array = np.pad(template_array, ((0, 0), (0, pad_width)), 'constant')
            
            # Show first 20 weeks for preview
            preview_weeks = min(20, template_array.shape[1])
            for day in range(self.GITHUB_DAYS):
                print("   ", end="")
                for week in range(preview_weeks):
                    intensity = template_array[day, week] if day < template_array.shape[0] else 0
                    if sys.stdout.isatty():  # Only use colors in terminal
                        print(self.GITHUB_COLORS.get(intensity, '  '), end="")
                    else:
                        chars = [' ', '░', '▒', '▓', '█']
                        print(chars[intensity], end="")
                print()
            print()
    
    def generate_text_image(self, text, font_size=8):
        """Generate an image from text"""
        # Create a large canvas first to get text dimensions
        temp_img = Image.new('L', (1000, 100), color=255)
        temp_draw = ImageDraw.Draw(temp_img)
        font = None
        font_paths = [
            os.path.join(os.path.dirname(__file__), 'DejaVuSansMono.ttf'),
            'DejaVuSansMono.ttf',
            'Courier.ttf',
            'courier.ttf'
        ]
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except Exception:
                continue
        if font is None:
            try:
                font = ImageFont.load_default()
                print("\n⚠️  Warning: No monospace font found. The output may look odd.\n" \
                      "For best results, install 'DejaVuSansMono.ttf' or 'Courier.ttf' and place it in the script directory.\n")
            except Exception:
                print("\n❌ Error: No usable font found. Please install a monospace font like 'DejaVuSansMono.ttf' and try again.\n")
                sys.exit(1)
        # Get text dimensions
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        # Create properly sized image
        img = Image.new('L', (text_width + 4, text_height + 4), color=255)
        draw = ImageDraw.Draw(img)
        # Draw text in black
        draw.text((2, 2), text, font=font, fill=0)
        return img
    
    def load_template(self, template_name):
        """Load a template pattern"""
        if template_name not in self.templates:
            print(f"Template '{template_name}' not found. Available templates:")
            for name in self.templates.keys():
                print(f"  - {name}")
            sys.exit(1)
        
        pattern = np.array(self.templates[template_name])
        
        # Pad to fit GitHub contribution graph dimensions
        if pattern.shape[0] < self.GITHUB_DAYS:
            pad_height = self.GITHUB_DAYS - pattern.shape[0]
            pattern = np.pad(pattern, ((0, pad_height), (0, 0)), 'constant')
        
        if pattern.shape[1] < self.GITHUB_WEEKS:
            pad_width = self.GITHUB_WEEKS - pattern.shape[1]
            pattern = np.pad(pattern, ((0, 0), (0, pad_width)), 'constant')
        elif pattern.shape[1] > self.GITHUB_WEEKS:
            pattern = pattern[:, :self.GITHUB_WEEKS]
        
        return pattern[:self.GITHUB_DAYS, :self.GITHUB_WEEKS]
    
    def load_and_process_image(self, image_path=None, text=None, template=None):
        """Load image, text, or template and convert to GitHub contribution format"""
        try:
            if template:
                return self.load_template(template)
            elif text:
                img = self.generate_text_image(text)
            else:
                img = Image.open(image_path).convert('L')
            
            # Resize to 52x7 (GitHub contribution graph dimensions)
            img = img.resize((self.GITHUB_WEEKS, self.GITHUB_DAYS), Image.Resampling.LANCZOS)
            
            # Convert to numpy array and normalize to 0-4 intensity levels
            img_array = np.array(img)
            
            # Invert (darker pixels = more contributions)
            img_array = 255 - img_array
            
            # Normalize to 0-4 range
            img_array = (img_array / 255.0 * self.MAX_INTENSITY).astype(int)
            
            return img_array
            
        except Exception as e:
            print(f"Error processing input: {e}")
            sys.exit(1)
    
    def preview_contribution_graph(self, image_path=None, text=None, template=None):
        """Preview the contribution graph without pushing to GitHub"""
        print("Processing input...")
        contribution_matrix = self.load_and_process_image(image_path, text, template)
        
        print("\n🎨 Preview of contribution graph:")
        if sys.stdout.isatty():
            print("(Using GitHub's actual colors)")
        else:
            print("(0 = no activity, 4 = highest activity)")
        print()
        
        # Print header with month indicators (approximate)
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        print("     ", end="")
        for i in range(0, self.GITHUB_WEEKS, 4):
            month_idx = (i // 4) % 12
            print(f"{months[month_idx]:<4}", end="")
        print()
        
        # Days of the week
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        
        for day in range(self.GITHUB_DAYS):
            print(f"{days[day]} ", end="")
            for week in range(self.GITHUB_WEEKS):
                intensity = contribution_matrix[day, week]
                
                # Use GitHub colors in terminal, fallback to characters elsewhere
                if sys.stdout.isatty():
                    print(self.GITHUB_COLORS.get(intensity, '  '), end="")
                else:
                    chars = [' ', '░', '▒', '▓', '█']
                    print(chars[intensity], end="")
                
            print()  # New line after each day
        
        print(f"\n📊 Statistics:")
        print(f"   Total contribution days: {np.sum(contribution_matrix > 0)}")
        print(f"   Total commits: {np.sum(contribution_matrix)}")
        print(f"   Max daily commits: {np.max(contribution_matrix)}")
        print(f"   Coverage: {np.sum(contribution_matrix > 0) / (self.GITHUB_WEEKS * self.GITHUB_DAYS) * 100:.1f}%")
    
    def generate_commit_dates(self, contribution_matrix, weeks_ago=0):
        """Generate commit dates based on contribution matrix"""
        commits = []
        
        # Calculate the start date (52 weeks ago from now, plus offset)
        today = datetime.now()
        start_date = today - timedelta(weeks=52 + weeks_ago)
        
        # Find the most recent Sunday to align with GitHub's week start
        days_since_sunday = start_date.weekday() + 1  # Monday is 0, so Sunday is 6
        if days_since_sunday == 7:
            days_since_sunday = 0
        start_date = start_date - timedelta(days=days_since_sunday)
        
        for week in range(self.GITHUB_WEEKS):
            for day in range(self.GITHUB_DAYS):
                intensity = contribution_matrix[day, week]
                if intensity > 0:
                    # Calculate the date for this day
                    commit_date = start_date + timedelta(weeks=week, days=day)
                    
                    # Add multiple commits for higher intensity
                    for commit_num in range(intensity):
                        # Spread commits throughout the day
                        hour = 9 + (commit_num * 3) % 14  # 9 AM to 11 PM
                        minute = (commit_num * 17) % 60
                        commit_time = commit_date.replace(hour=hour, minute=minute)
                        commits.append(commit_time)
        
        return commits
    
    def push_to_github(self, repo, branch="contribution", weeks_ago=0, 
                      image_path=None, text=None, template=None, dry_run=False):
        """Create commits and push to GitHub repository"""
        global GITHUB_PAT
        if not self.check_git_requirements():
            print("\nPlease make sure Git is installed and configured before continuing.\nYou can download Git from https://git-scm.com/downloads\n")
            return
        print("Processing input...")
        contribution_matrix = self.load_and_process_image(image_path, text, template)
        print("Generating commit dates...")
        commit_dates = self.generate_commit_dates(contribution_matrix, weeks_ago)
        if not commit_dates:
            print("❌ No commits to create (input is empty or too light). Try using a darker image, bolder text, or a different template.")
            return
        print(f"📅 Will create {len(commit_dates)} commits over {np.sum(contribution_matrix > 0)} days")
        print("\n🔍 Quick preview:")
        for day in range(min(7, self.GITHUB_DAYS)):
            print("   ", end="")
            for week in range(min(20, self.GITHUB_WEEKS)):
                intensity = contribution_matrix[day, week]
                if sys.stdout.isatty():
                    print(self.GITHUB_COLORS.get(intensity, '  '), end="")
                else:
                    chars = [' ', '░', '▒', '▓', '█']
                    print(chars[intensity], end="")
            print()
        print(f"\n⚠️  This will create {len(commit_dates)} commits in your repository: {repo}")
        print("This will overwrite the branch if it already exists.")
        if dry_run:
            print("\n[DRY RUN] No changes will be made. This is a simulation.\n")
            return
        response = input("Do you want to continue? Type 'yes' to proceed, or anything else to cancel: ")
        if response.lower() != 'yes':
            print("Cancelled. No changes were made.")
            return
        with tempfile.TemporaryDirectory() as temp_dir:
            self.create_git_repository(temp_dir, repo, branch, commit_dates, 
                                     image_path, text, template)
    
    def check_git_requirements(self):
        """Check if git is available and configured"""
        try:
            # Check if git is installed
            subprocess.run(['git', '--version'], check=True, capture_output=True)
            
            # Check if git is configured
            try:
                subprocess.run(['git', 'config', 'user.name'], check=True, capture_output=True)
                subprocess.run(['git', 'config', 'user.email'], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                print("❌ Git is not configured. Please set your name and email:")
                print("   git config --global user.name 'Your Name'")
                print("   git config --global user.email 'your.email@example.com'")
                return False
                
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Git is not installed or not available in PATH")
            return False
    
    def create_git_repository(self, temp_dir, repo, branch, commit_dates, 
                            image_path=None, text=None, template=None):
        """Create git repository and commits"""
        global GITHUB_PAT
        prev_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            # Initialize git repository
            subprocess.run(['git', 'init'], check=True, capture_output=True)
            subprocess.run(['git', 'checkout', '-b', branch], check=True, capture_output=True)
            
            # Add remote
            if GITHUB_PAT:
                remote_url = f"https://{GITHUB_PAT}:x-oauth-basic@github.com/{repo}.git"
            else:
                remote_url = f"git@github.com:{repo}.git"
            subprocess.run(['git', 'remote', 'add', 'origin', remote_url], check=True, capture_output=True)
            
            # Create README with art info
            source_info = ""
            if image_path:
                source_info = f"Image: {os.path.basename(image_path)}"
            elif text:
                source_info = f"Text: '{text}'"
            elif template:
                source_info = f"Template: {template}"
            
            readme_content = f"""# Contribution Graph Art

{source_info}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This repository contains contribution graph art created with a Python script.
Each commit represents a pixel in the final image on the GitHub contribution graph.

Total commits: {len(commit_dates)}
"""
            
            with open('README.md', 'w') as f:
                f.write(readme_content)
            
            # Create commits with custom dates
            print("🚀 Creating commits...")
            total_commits = len(commit_dates)
            
            for i, commit_date in enumerate(commit_dates):
                # Update README to make each commit unique
                with open('README.md', 'a') as f:
                    f.write(f"\n<!-- Commit {i+1} at {commit_date} -->")
                
                subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
                
                # Format date for git
                date_str = commit_date.strftime("%Y-%m-%d %H:%M:%S")
                
                # Create commit with custom date
                env = os.environ.copy()
                env['GIT_AUTHOR_DATE'] = date_str
                env['GIT_COMMITTER_DATE'] = date_str
                
                commit_msg = f"Art pixel {i+1}/{total_commits}"
                subprocess.run([
                    'git', 'commit', '-m', commit_msg
                ], env=env, check=True, capture_output=True)
                
                # Progress indicator
                if (i + 1) % 25 == 0 or i == total_commits - 1:
                    progress = (i + 1) / total_commits * 100
                    print(f"   Progress: {i+1}/{total_commits} ({progress:.1f}%)")
            
            print("✅ All commits created!")
            
            # Push to GitHub
            print("📤 Pushing to GitHub...")
            result = subprocess.run(['git', 'push', '-u', 'origin', branch], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"🎉 Successfully pushed to {repo}!")
                print(f"🔗 View at: https://github.com/{repo}")
                print(f"📊 Contribution graph: https://github.com/{repo.split('/')[0]}")
                open_browser = input("Would you like to open your repository in your web browser now? (y/N): ")
                if open_browser.strip().lower() == 'y':
                    webbrowser.open(f"https://github.com/{repo}")
            else:
                print(f"❌ Error pushing to GitHub: {result.stderr}\nPlease check your repository name, your network connection, and that you have write access.")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}\nPlease check your Git configuration and try again.")
        except Exception as e:
            print(f"❌ Error: {e}\nIf you need help, please check the documentation or ask for support.")
        finally:
            os.chdir(prev_cwd)

    def import_templates(self, json_path):
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                print("❌ Invalid template file format.")
                return
            self.templates.update(data)
            print(f"✅ Imported {len(data)} templates from {json_path}.")
        except Exception as e:
            print(f"❌ Error importing templates: {e}")

    def export_templates(self, json_path):
        try:
            with open(json_path, 'w') as f:
                json.dump(self.templates, f, indent=2)
            print(f"✅ Exported {len(self.templates)} templates to {json_path}.")
        except Exception as e:
            print(f"❌ Error exporting templates: {e}")

    def fetch_community_templates(self, url):
        print("(Community template fetch not yet implemented. Placeholder.)")
        # Placeholder for future implementation
        # Example: requests.get(url), then self.templates.update(...)


def get_stored_pat():
    return keyring.get_password(GITHUB_KEYRING_SERVICE, 'github_pat')

def save_pat(pat):
    keyring.set_password(GITHUB_KEYRING_SERVICE, 'github_pat', pat)

def connect_github_account():
    global GITHUB_PAT
    print("\nTo push to your GitHub account, you can use a Personal Access Token (PAT).\n")
    print("If you don't have one, you can create it here: https://github.com/settings/tokens\n")
    print("Recommended scopes: 'repo' (for private repos) or 'public_repo' (for public repos).\n")
    pat = input("Paste your GitHub Personal Access Token (PAT): ").strip()
    if not pat:
        print("No token entered. Returning to wizard menu.\n")
        return
    # Test the PAT
    headers = {"Authorization": f"token {pat}"}
    try:
        resp = requests.get("https://api.github.com/user", headers=headers, timeout=10)
        if resp.status_code == 200:
            user = resp.json().get('login', '(unknown)')
            print(f"✅ Successfully connected as GitHub user: {user}\n")
            GITHUB_PAT = pat
            save = input("Would you like to save this PAT securely for future use? (y/N): ").strip().lower()
            if save == 'y':
                save_pat(pat)
                print("PAT saved securely.\n")
        else:
            print(f"❌ Failed to authenticate with GitHub. Status: {resp.status_code}. Please check your token and try again.\n")
    except Exception as e:
        print(f"❌ Error connecting to GitHub: {e}\n")

# On startup, try to load a stored PAT
GITHUB_PAT = get_stored_pat() or None

I18N = {
    'en': {
        'welcome': "Welcome to the GitHub Contribution Graph Art Wizard!",
        'guided_mode': "This guided mode will help you create art on your GitHub contribution graph step by step.",
        'choose_action': "What would you like to do?",
        'preview': "Preview a contribution graph",
        'push': "Push art to a GitHub repository",
        'list_templates': "List available templates",
        'import_templates': "Import templates from JSON file",
        'export_templates': "Export current templates to JSON file",
        'fetch_community': "Fetch community templates (coming soon)",
        'connect_github': "Connect your GitHub account (Personal Access Token)",
        'exit': "Exit",
        'invalid_choice': "Invalid choice. Please enter a valid number.",
        'select_lang': "Select your language (en = English, ...): ",
        'lang_set': "Language set to: "
    },
    # Placeholder for other languages
}
LANG = 'en'
def _(key):
    return I18N.get(LANG, I18N['en']).get(key, key)

def wizard_mode():
    global LANG
    lang = input(_( 'select_lang')).strip().lower() or 'en'
    if lang in I18N:
        LANG = lang
        print(_( 'lang_set') + lang)
    print(f"\n{_('welcome')}\n")
    print(f"{_('guided_mode')}\n")
    generator = ContributionGenerator()
    while True:
        print(_( 'choose_action'))
        print(f"  1. {_('preview')}")
        print(f"  2. {_('push')}")
        print(f"  3. {_('list_templates')}")
        print(f"  4. {_('import_templates')}")
        print(f"  5. {_('export_templates')}")
        print(f"  6. {_('fetch_community')}")
        print(f"  7. {_('connect_github')}")
        print(f"  8. {_('exit')}")
        choice = input("Enter the number of your choice: ").strip()
        if choice == '1':
            input_type = ''
            while input_type not in ['1', '2', '3']:
                print("\nHow would you like to create your art?")
                print("  1. From an image file")
                print("  2. From text")
                print("  3. From a template")
                input_type = input("Enter 1, 2, or 3: ").strip()
            img = text = template = None
            if input_type == '1':
                img = input("Enter the path to your image file: ").strip()
                if not os.path.exists(img):
                    print(f"❌ Error: Image file '{img}' not found\n")
                    continue
            elif input_type == '2':
                text = input("Enter the text to display: ").strip()
            else:
                print("Available templates:")
                for t in generator.templates:
                    print(f"  - {t}")
                template = input("Enter the template name: ").strip()
            # Show preview in terminal
            generator.preview_contribution_graph(img, text, template)
            # Ask if user wants to see a pop-up image preview
            show_img = input("Would you like to see a pop-up image preview? (y/N): ").strip().lower()
            if show_img == 'y':
                # Generate the image and show it
                if template:
                    arr = generator.load_template(template)
                    img_obj = Image.fromarray((arr / generator.MAX_INTENSITY * 255).astype('uint8'))
                elif text:
                    img_obj = generator.generate_text_image(text)
                else:
                    img_obj = Image.open(img).convert('L')
                img_obj.show()
        elif choice == '2':
            input_type = ''
            while input_type not in ['1', '2', '3']:
                print("\nHow would you like to create your art?")
                print("  1. From an image file")
                print("  2. From text")
                print("  3. From a template")
                input_type = input("Enter 1, 2, or 3: ").strip()
            img = text = template = None
            if input_type == '1':
                img = input("Enter the path to your image file: ").strip()
                if not os.path.exists(img):
                    print(f"❌ Error: Image file '{img}' not found\n")
                    continue
            elif input_type == '2':
                text = input("Enter the text to display: ").strip()
            else:
                print("Available templates:")
                for t in generator.templates:
                    print(f"  - {t}")
                template = input("Enter the template name: ").strip()
            repo = input("Enter your GitHub repository (username/repo): ").strip()
            branch = input("Enter the branch name (default: contribution): ").strip() or 'contribution'
            weeks_ago = input("Offset pattern by how many weeks? (default: 0): ").strip()
            try:
                weeks_ago = int(weeks_ago) if weeks_ago else 0
            except ValueError:
                weeks_ago = 0
            dry_run = input("Would you like to do a dry run (simulate push, no changes)? (y/N): ").strip().lower() == 'y'
            generator.push_to_github(repo, branch, weeks_ago, img, text, template, dry_run=dry_run)
        elif choice == '3':
            generator.list_templates()
        elif choice == '4':
            path = input("Enter the path to the JSON file to import: ").strip()
            generator.import_templates(path)
        elif choice == '5':
            path = input("Enter the path to save the exported JSON file: ").strip()
            generator.export_templates(path)
        elif choice == '6':
            print("Fetching community templates is not yet implemented. Stay tuned!")
        elif choice == '7':
            connect_github_account()
        elif choice == '8':
            print("Goodbye!")
            break
        else:
            print(_( 'invalid_choice') + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="🎨 Draw images, text, or templates on your GitHub contribution graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python contribution.py preview -img skull.png
  python contribution.py preview -text "HIRE ME" 
  python contribution.py preview -template heart
  python contribution.py push -text "PYTHON" -repo myuser/contribution-art
  python contribution.py list-templates
  python contribution.py --wizard
  python contribution.py
  
🚨 Important: Create an empty GitHub repository first!
        """
    )
    parser.add_argument('--wizard', action='store_true', help='Launch interactive guided mode')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List templates command
    list_parser = subparsers.add_parser('list-templates', help='Show available templates')
    
    # Preview command
    preview_parser = subparsers.add_parser('preview', help='Preview contribution graph')
    input_group = preview_parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-img', help='Path to image file')
    input_group.add_argument('-text', help='Text to convert to pixels')
    input_group.add_argument('-template', help='Template name (use list-templates to see options)')
    
    # Push command  
    push_parser = subparsers.add_parser('push', help='Push contribution graph to GitHub')
    push_input_group = push_parser.add_mutually_exclusive_group(required=True)
    push_input_group.add_argument('-img', help='Path to image file')
    push_input_group.add_argument('-text', help='Text to convert to pixels') 
    push_input_group.add_argument('-template', help='Template name')
    push_parser.add_argument('-repo', required=True, help='GitHub repository (username/repo)')
    push_parser.add_argument('-branch', default='contribution', help='Git branch (default: contribution)')
    push_parser.add_argument('-w', type=int, default=0, 
                           help='Weeks ago offset (moves pattern left)')
    
    args = parser.parse_args()
    
    if args.wizard or len(sys.argv) == 1:
        wizard_mode()
        return
    
    if not args.command:
        parser.print_help()
        return
    
    generator = ContributionGenerator()
    
    if args.command == 'list-templates':
        generator.list_templates()
    elif args.command == 'preview':
        # Check if image file exists (only for image input)
        if args.img and not os.path.exists(args.img):
            print(f"❌ Error: Image file '{args.img}' not found")
            sys.exit(1)
        generator.preview_contribution_graph(args.img, args.text, args.template)
    elif args.command == 'push':
        # Check if image file exists (only for image input)
        if args.img and not os.path.exists(args.img):
            print(f"❌ Error: Image file '{args.img}' not found")
            sys.exit(1)
        generator.push_to_github(args.repo, args.branch, args.w, 
                               args.img, args.text, args.template)


if __name__ == "__main__":
    main()
