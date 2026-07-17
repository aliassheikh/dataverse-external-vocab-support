import os
import sys
import json
import shutil
import subprocess
import importlib.util

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Import compose_cvoc_config from compose-cvoc-conf.py
spec = importlib.util.spec_from_file_location("compose_cvoc_conf", os.path.join(SCRIPTS_DIR, "compose-cvoc-conf.py"))
compose_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compose_module)
compose_cvoc_config = compose_module.compose_cvoc_config

ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
SERVICES_DIR = os.path.join(ROOT_DIR, 'services')
DIST_DIR = os.path.join(ROOT_DIR, 'dist', 'js')
DEFAULT_OUTPUT = 'CVocConf.json'

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def create_symlink(target, link):
    if os.path.exists(link):
        if os.path.islink(link) or os.path.isfile(link):
            os.remove(link)
        elif os.path.isdir(link):
            shutil.rmtree(link)
    
    relative_target = os.path.relpath(target, os.path.dirname(link))
    try:
        # On Windows, try to use junction for directories
        is_dir = os.path.isdir(target)
        if os.name == 'nt' and is_dir:
            subprocess.check_call(['cmd', '/c', 'mklink', '/j', link, target], shell=True)
        else:
            os.symlink(relative_target, link, target_is_directory=is_dir)
        print(f"Linked: {os.path.basename(link)} -> {relative_target}")
    except Exception as e:
        print(f"Failed to link {link}: {e}")
        print("Attempting copy instead...")
        if os.path.isdir(target):
            shutil.copytree(target, link)
        else:
            shutil.copy2(target, link)
        print(f"Copied: {os.path.basename(link)}")

def link_services():
    print('Populating dist/ directory...')
    ensure_dir(DIST_DIR)
    ensure_dir(os.path.join(DIST_DIR, 'i18n'))

    if not os.path.exists(SERVICES_DIR):
        print(f"Error: {SERVICES_DIR} not found.")
        return

    for service in os.listdir(SERVICES_DIR):
        service_path = os.path.join(SERVICES_DIR, service)
        if not os.path.isdir(service_path):
            continue

        # Link JS files
        for file in os.listdir(service_path):
            if file.endswith('.js'):
                create_symlink(os.path.join(service_path, file), os.path.join(DIST_DIR, file))

        # Link i18n files
        i18n_dir = os.path.join(service_path, 'i18n')
        if os.path.exists(i18n_dir) and os.path.isdir(i18n_dir):
            for file in os.listdir(i18n_dir):
                if file.endswith('.json'):
                    create_symlink(os.path.join(i18n_dir, file), os.path.join(DIST_DIR, 'i18n', file))

def list_configs():
    configs = []
    if not os.path.exists(SERVICES_DIR):
        return configs

    for service in os.listdir(SERVICES_DIR):
        config_dir = os.path.join(SERVICES_DIR, service, 'configs')
        if os.path.exists(config_dir) and os.path.isdir(config_dir):
            for file in os.listdir(config_dir):
                if file.endswith('.json'):
                    configs.append({
                        'service': service,
                        'name': file,
                        'path': os.path.join(config_dir, file)
                    })
    return configs

def rewrite_js_urls(config_path, base_url):
    if not base_url:
        return
    
    print(f"Rewriting JS URLs to base: {base_url}")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    for item in config:
        if 'js-url' in item and isinstance(item['js-url'], list):
            item['js-url'] = [
                f"{base_url.rstrip('/')}/{os.path.basename(url)}"
                for url in item['js-url']
            ]
        elif 'js-url' in item and isinstance(item['js-url'], str):
             item['js-url'] = f"{base_url.rstrip('/')}/{os.path.basename(item['js-url'])}"

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def compose():
    available_configs = list_configs()
    print('\nAvailable configurations:')
    for i, cfg in enumerate(available_configs):
        print(f"{i + 1}: [{cfg['service']}] {cfg['name']}")

    selection = input('\nEnter numbers of configs to include (comma separated, or "all"): ')
    selected_configs = []

    if selection.lower() == 'all':
        selected_configs = available_configs
    else:
        try:
            indices = [int(s.strip()) - 1 for s in selection.split(',')]
            selected_configs = [available_configs[i] for i in indices if 0 <= i < len(available_configs)]
        except ValueError:
            print("Invalid input.")
            return

    if not selected_configs:
        print('No configurations selected.')
        return

    output_file = input(f"Output filename (default: {DEFAULT_OUTPUT}): ") or DEFAULT_OUTPUT
    
    compose_cvoc_config([cfg['path'] for cfg in selected_configs], output_file)

    rewrite = input('\nRewrite js-url to a local base URL? (y/N): ')
    if rewrite.lower() == 'y':
        base_url = input('Enter local base URL (e.g., http://localhost/js/): ')
        rewrite_js_urls(output_file, base_url)

    print(f"\nConfiguration saved to {output_file}")

def publish():
    config_file = input(f"Configuration file to upload (default: {DEFAULT_OUTPUT}): ") or DEFAULT_OUTPUT
    
    if not os.path.exists(config_file):
        print(f"Error: File {config_file} not found.")
        return

    dv_url = input('Dataverse URL (e.g., http://localhost:8080): ')
    api_key = input('API Key: ')

    endpoint = f"{dv_url.rstrip('/')}/api/admin/settings/:CVocConf"

    print(f"Uploading {config_file} to {endpoint}...")

    try:
        command = ['curl', '-X', 'PUT', '--upload-file', config_file, '-H', f"X-Dataverse-key: {api_key}", endpoint]
        result = subprocess.run(command, capture_output=True, text=True)
        print('\nResponse from Dataverse:')
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except Exception as e:
        print(f"\nFailed to upload: {e}")

def main():
    if len(sys.argv) < 2:
        command = 'help'
    else:
        command = sys.argv[1]

    if command == 'link':
        link_services()
    elif command == 'compose':
        compose()
    elif command == 'publish':
        publish()
    else:
        print('Usage: python scripts/deploy.py [command]')
        print('Commands:')
        print('  link     Populate dist/ directory with symlinks to services')
        print('  compose  Interactively select and combine configurations')
        print('  publish  Upload a configuration to Dataverse API')

if __name__ == "__main__":
    main()
