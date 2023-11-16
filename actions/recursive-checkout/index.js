const core = require('@actions/core');
const exec = require('@actions/exec');
const fs = require('fs');
const path = require('path');
const minimatch = require('minimatch');
const gitUrlParse = require('git-url-parse');

async function run() {
    try {
        const repoDataLines = core.getInput('repoData').split('\n');
        const excludePatterns = core.getInput('exclude').split('\n').filter(p => p.trim() !== '');

        let repos = {};
        for (const line of repoDataLines) {
            if (line.trim() === '') continue;
            const [repoFullName, sha] = line.split(':').map(part => part.trim());
            repos[repoFullName] = sha;
        }

        function shouldExclude(filePath) {
            return excludePatterns.some(pattern => minimatch(filePath, pattern));
        }

        async function getGitRepoName(dir) {
            try {
                const repoUrl = await exec.getExecOutput('git', ['config', '--get', 'remote.origin.url'], {
                    cwd: dir
                });
                if (repoUrl.stdout) {
                    const parsedUrl = gitUrlParse(repoUrl.stdout.trim());
                    return `${parsedUrl.owner}/${parsedUrl.name}`;
                }
            } catch (error) {
                core.warning(`Failed to get Git repo name for ${dir}: ${error}`);
            }
            return null;
        }

        async function checkoutRepo(dir, sha) {
            try {
                // Check if SHA exists locally
                const shaExists = await exec.getExecOutput('git', ['cat-file', '-t', sha], {
                    cwd: dir,
                    ignoreReturnCode: true
                });
                if (shaExists.exitCode !== 0) {
                    // Fetch the specific SHA
                    await exec.exec('git', ['fetch', '--depth=1', 'origin', sha], {
                        cwd: dir
                    });
                }
                // Checkout the SHA
                await exec.exec('git', ['-C', dir, 'checkout', sha]);
            } catch (error) {
                core.error(`Failed to checkout ${sha} in ${dir}: ${error}`);
            }
        }

        async function processDirectory(dir) {
            const entries = fs.readdirSync(dir, {
                withFileTypes: true
            });

            for (const entry of entries) {
                const fullPath = path.join(dir, entry.name);

                if (entry.isDirectory()) {
                    if (!shouldExclude(fullPath)) {
                        if (entry.name === '.git') {
                            const repoName = await getGitRepoName(dir);
                            if (repoName && repos[repoName]) {
                                const sha = repos[repoName];
                                await checkoutRepo(dir, sha);
                            }
                        } else {
                            await processDirectory(fullPath);
                        }
                    }
                }
            }
        }

        await processDirectory('.'); // Start processing from the current working directory
    } catch (error) {
        core.setFailed(`Action failed with error: ${error}`);
    }
}

run();
