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
DIST_ROOT = os.path.join(ROOT_DIR, 'dist')
DIST_DIR = os.path.join(DIST_ROOT, 'js')
DIST_IMG_DIR = os.path.join(DIST_ROOT, 'img')
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
    ensure_dir(DIST_IMG_DIR)

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

        # Link img files
        img_dir = os.path.join(service_path, 'img')
        if os.path.exists(img_dir) and os.path.isdir(img_dir):
            for file in os.listdir(img_dir):
                create_symlink(os.path.join(img_dir, file), os.path.join(DIST_IMG_DIR, file))

def list_configs():
    configs = []
    if not os.path.exists(SERVICES_DIR):
        return configs

    for service in os.listdir(SERVICES_DIR):
        config_dir = os.path.join(SERVICES_DIR, service, 'configs')
        if os.path.exists(config_dir) and os.path.isdir(config_dir):
            for file in os.listdir(config_dir):
                if file.endswith('.json') and not file.endswith('.schema.json'):
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

    config_list = config if isinstance(config, list) else [config]
    for item in config_list:
        if 'js-url' in item:
            urls = item['js-url'] if isinstance(item['js-url'], list) else [item['js-url']]
            updated_urls = []
            for url in urls:
                file_name = os.path.basename(url)
                # The base URL now points to the dist root, so we add /js/
                updated_urls.append(f"{base_url.rstrip('/')}/js/{file_name}")
            item['js-url'] = updated_urls if isinstance(item['js-url'], list) else updated_urls[0]

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
        print('\nNote: The base URL should be the location where the dist/ directory will be linked (e.g., the URL of your cvoc directory).')
        base_url = input('Enter local base URL (e.g., http://localhost/cvoc/): ')
        rewrite_js_urls(output_file, base_url)

    print(f"\nConfiguration saved to {output_file}")

def update_dataverse():
    config_file = input(f"Configuration file to upload (default: {DEFAULT_OUTPUT}): ") or DEFAULT_OUTPUT
    
    if not os.path.exists(config_file):
        print(f"Error: File {config_file} not found.")
        return

    dv_url = input('Dataverse URL (default: http://localhost:8080/): ') or 'http://localhost:8080/'
    unblock_key = input('Unblock Key (optional, if required by your Dataverse): ')

    endpoint = dv_url.rstrip('/') + '/api/admin/settings/:CVocConf'
    if unblock_key:
        endpoint += f"?unblock-key={unblock_key}"

    masked_endpoint = endpoint.replace(unblock_key, '********') if unblock_key else endpoint
    print(f"Uploading {config_file} to {masked_endpoint}...")

    try:
        command = ['curl', '-X', 'PUT', '--upload-file', config_file, endpoint]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        print('\nResponse from Dataverse:')
        print(result.stdout)
        if result.returncode == 0:
            print('\nSuccess: The :CVocConf setting has been updated and scripts that have been linked and composed with this script should now be active.')
            print('Note: Individual scripts may also require specific metadata blocks or other configuration and users should review the instructions for the scripts they use.')
        else:
            print(f"\nFailed to upload. Exit code: {result.returncode}")
            masked_command = f"curl -X PUT --upload-file \"{config_file}\" \"{masked_endpoint}\""
            print(f"Attempted command: {masked_command}")
            if result.stderr:
                print(result.stderr)
    except Exception as e:
        print(f"\nFailed to upload: {e}")
        masked_command = f"curl -X PUT --upload-file \"{config_file}\" \"{masked_endpoint}\""
        print(f"Attempted command: {masked_command}")

def link_web():
    print('\nThis step will link your dist/ directory (containing js and img) to your web server.')
    
    config_file = input(f"Reference configuration file to check for base URL (default: {DEFAULT_OUTPUT}): ") or DEFAULT_OUTPUT
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                config_list = config if isinstance(config, list) else [config]
                
                found = False
                for item in config_list:
                    if 'js-url' in item:
                        js_url = item['js-url'][0] if isinstance(item['js-url'], list) else item['js-url']
                        if js_url:
                            script_dir = js_url[:js_url.rfind('/')]
                            print(f"\nBased on {config_file}, your scripts are configured to be in: {script_dir}/")
                            if '/js/' in js_url:
                                base_url = js_url[:js_url.rfind('/js/')]
                                print(f"You should link the dist/ directory to the local directory corresponding to the web path: {base_url}")
                            else:
                                print("Note: Could not automatically determine the base directory from this URL.")
                            found = True
                            break
                if not found:
                    print(f"\nNo 'js-url' found in {config_file}.")
        except Exception as e:
            print(f"\nError parsing {config_file}: {e}")
    else:
        print(f"\nFile {config_file} not found. Skipping URL detection.")

    print('\nIt is recommended to link the entire dist/ directory so that both scripts and images are available.')
    
    web_path = input('Enter the target path on your web server (the local directory corresponding to the web path used in the compose step): ')
    if not web_path:
        print('No path provided. Skipping.')
        return

    if os.path.exists(web_path):
        print(f"\nNote: {web_path} already exists. Skipping link creation.")
        return

    absolute_dist = os.path.abspath(DIST_ROOT)
    print(f"Linking {absolute_dist} to {web_path}...")

    try:
        if os.name == 'nt':
            # Use junction for directories on Windows
            subprocess.check_call(['cmd', '/c', 'mklink', '/j', web_path, absolute_dist], shell=True)
        else:
            os.symlink(absolute_dist, web_path)
        print(f"\nSuccess: Linked {absolute_dist} to {web_path}")
    except Exception as e:
        print(f"\nFailed to create link: {e}")
        print('\nPlease run the following command manually (possibly with sudo):')
        if os.name == 'nt':
            print(f"  mklink /j \"{web_path}\" \"{absolute_dist}\"")
        else:
            print(f"  sudo ln -s \"{absolute_dist}\" \"{web_path}\"")

def main():
    if len(sys.argv) < 2:
        command = 'help'
    else:
        command = sys.argv[1]

    if command == 'link':
        link_services()
    elif command == 'compose':
        compose()
    elif command == 'updateDataverse':
        update_dataverse()
    elif command == 'linkWeb':
        link_web()
    else:
        print('Usage: python scripts/deploy.py [command]')
        print('Commands:')
        print('  link     Populate dist/ directory with symlinks to services')
        print('  linkWeb  Link the dist/ directory to your web server')
        print('  compose  Interactively select and combine configurations')
        print('  updateDataverse  Upload a configuration to Dataverse API')

if __name__ == "__main__":
    main()
