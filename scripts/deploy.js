const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const readline = require('readline');
const { composeCvocConfig } = require('./compose-cvoc-conf');

const SERVICES_DIR = path.join(__dirname, '..', 'services');
const DIST_DIR = path.join(__dirname, '..', 'dist', 'js');
const DEFAULT_OUTPUT = 'CVocConf.json';

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

const question = (query) => new Promise((resolve) => rl.question(query, resolve));

/**
 * Ensures a directory exists.
 */
function ensureDir(dir) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
}

/**
 * Creates a symlink, handling existing ones.
 */
function createSymlink(target, link) {
    if (fs.existsSync(link)) {
        const stats = fs.lstatSync(link);
        if (stats.isSymbolicLink() || stats.isFile() || stats.isDirectory()) {
            fs.rmSync(link, { recursive: true, force: true });
        }
    }
    
    const relativeTarget = path.relative(path.dirname(link), target);
    try {
        const type = fs.statSync(target).isDirectory() ? 'junction' : 'file';
        fs.symlinkSync(relativeTarget, link, type);
        console.log(`Linked: ${path.basename(link)} -> ${relativeTarget}`);
    } catch (err) {
        console.error(`Failed to link ${link}: ${err.message}`);
        console.log(`Attempting copy instead...`);
        fs.cpSync(target, link, { recursive: true });
        console.log(`Copied: ${path.basename(link)}`);
    }
}

/**
 * Populates the dist directory with symlinks to service files.
 */
function linkServices() {
    console.log('Populating dist/ directory...');
    ensureDir(DIST_DIR);
    ensureDir(path.join(DIST_DIR, 'i18n'));

    const services = fs.readdirSync(SERVICES_DIR);

    services.forEach(service => {
        const servicePath = path.join(SERVICES_DIR, service);
        if (!fs.statSync(servicePath).isDirectory()) return;

        // Link JS files
        const files = fs.readdirSync(servicePath);
        files.forEach(file => {
            if (file.endsWith('.js')) {
                createSymlink(path.join(servicePath, file), path.join(DIST_DIR, file));
            }
        });

        // Link i18n files
        const i18nDir = path.join(servicePath, 'i18n');
        if (fs.existsSync(i18nDir) && fs.statSync(i18nDir).isDirectory()) {
            const i18nFiles = fs.readdirSync(i18nDir);
            i18nFiles.forEach(file => {
                if (file.endsWith('.json')) {
                    createSymlink(path.join(i18nDir, file), path.join(DIST_DIR, 'i18n', file));
                }
            });
        }
    });
}

/**
 * Lists all available configurations.
 */
function listConfigs() {
    const services = fs.readdirSync(SERVICES_DIR);
    const configs = [];

    services.forEach(service => {
        const configDir = path.join(SERVICES_DIR, service, 'configs');
        if (fs.existsSync(configDir) && fs.statSync(configDir).isDirectory()) {
            const files = fs.readdirSync(configDir);
            files.forEach(file => {
                if (file.endsWith('.json')) {
                    configs.push({
                        service,
                        name: file,
                        path: path.join(configDir, file)
                    });
                }
            });
        }
    });

    return configs;
}

/**
 * Rewrites js-url in the configuration.
 */
function rewriteJsUrls(configPath, baseUrl) {
    if (!baseUrl) return;
    
    console.log(`Rewriting JS URLs to base: ${baseUrl}`);
    const content = fs.readFileSync(configPath, 'utf8');
    const config = JSON.parse(content);

    const updatedConfig = config.map(item => {
        if (item['js-url'] && Array.isArray(item['js-url'])) {
            item['js-url'] = item['js-url'].map(url => {
                const fileName = path.basename(url);
                return `${baseUrl.replace(/\/$/, '')}/${fileName}`;
            });
        }
        return item;
    });

    fs.writeFileSync(configPath, JSON.stringify(updatedConfig, null, 2), 'utf8');
}

/**
 * Interactive composition command.
 */
async function compose() {
    const availableConfigs = listConfigs();
    console.log('\nAvailable configurations:');
    availableConfigs.forEach((cfg, index) => {
        console.log(`${index + 1}: [${cfg.service}] ${cfg.name}`);
    });

    const selection = await question('\nEnter numbers of configs to include (comma separated, or "all"): ');
    let selectedConfigs = [];

    if (selection.toLowerCase() === 'all') {
        selectedConfigs = availableConfigs;
    } else {
        const indices = selection.split(',').map(s => parseInt(s.trim()) - 1);
        selectedConfigs = indices.map(i => availableConfigs[i]).filter(cfg => cfg);
    }

    if (selectedConfigs.length === 0) {
        console.log('No configurations selected.');
        return;
    }

    const outputFile = await question(`Output filename (default: ${DEFAULT_OUTPUT}): `) || DEFAULT_OUTPUT;
    
    composeCvocConfig(selectedConfigs.map(cfg => cfg.path), outputFile);

    const rewrite = await question('\nRewrite js-url to a local base URL? (y/N): ');
    if (rewrite.toLowerCase() === 'y') {
        const baseUrl = await question('Enter local base URL (e.g., http://localhost/js/): ');
        rewriteJsUrls(outputFile, baseUrl);
    }

    console.log(`\nConfiguration saved to ${outputFile}`);
}

/**
 * Interactive publish command.
 */
async function publish() {
    const configFile = await question(`Configuration file to upload (default: ${DEFAULT_OUTPUT}): `) || DEFAULT_OUTPUT;
    
    if (!fs.existsSync(configFile)) {
        console.error(`Error: File ${configFile} not found.`);
        return;
    }

    const dvUrl = await question('Dataverse URL (e.g., http://localhost:8080): ');
    const apiKey = await question('API Key: ');

    const endpoint = `${dvUrl.replace(/\/$/, '')}/api/admin/settings/:CVocConf`;

    console.log(`Uploading ${configFile} to ${endpoint}...`);

    try {
        // Using curl via execSync for simplicity as requested in requirements
        const command = `curl -X PUT --upload-file "${configFile}" -H "X-Dataverse-key: ${apiKey}" "${endpoint}"`;
        const result = execSync(command, { encoding: 'utf8' });
        console.log('\nResponse from Dataverse:');
        console.log(result);
    } catch (err) {
        console.error(`\nFailed to upload: ${err.message}`);
        if (err.stdout) console.log(err.stdout);
        if (err.stderr) console.error(err.stderr);
    }
}

async function main() {
    const args = process.argv.slice(2);
    const command = args[0] || 'help';

    switch (command) {
        case 'link':
            linkServices();
            rl.close();
            break;
        case 'compose':
            await compose();
            rl.close();
            break;
        case 'publish':
            await publish();
            rl.close();
            break;
        case 'help':
        default:
            console.log('Usage: node scripts/deploy.js [command]');
            console.log('Commands:');
            console.log('  link     Populate dist/ directory with symlinks to services');
            console.log('  compose  Interactively select and combine configurations');
            console.log('  publish  Upload a configuration to Dataverse API');
            rl.close();
            break;
    }
}

main();
