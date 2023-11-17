const core = require('@actions/core');
const exec = require('@actions/exec');
const glob = require('@actions/glob');
const fs = require('fs');
const path = require('path');
const gitUrlParse = require('git-url-parse');


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

async function checkoutRepo(dir, ref) {
    try {
        // Check if ref exists locally
        const refExists = await exec.getExecOutput('git', ['cat-file', '-t', ref], {
            cwd: dir,
            ignoreReturnCode: true
        });
        if (refExists.exitCode !== 0) {
            // Fetch the specific ref
            await exec.exec('git', ['fetch', '--depth=1', 'origin', ref], {
                cwd: dir
            });
        }
        // Checkout the ref
        await exec.exec('git', ['-C', dir, 'checkout', ref]);
    } catch (error) {
        core.error(`Failed to checkout ${ref} in ${dir}: ${error}`);
    }
}

async function main() {
    try {
        const repoDataLines = core.getMultilineInput('refs');
        const excludePatterns = core.getMultilineInput('exclude');
        const pathsToCheckout = core.getMultilineInput('paths');

        let repos = {};
        for (const line of repoDataLines) {
            if (line.trim() === '') continue;
            const [repoFullName, ref] = line.split(':').map(part => part.trim());
            repos[repoFullName] = ref;
        }

        const excludeGlobber = await glob.create(excludePatterns.join('\n'), { implicitDescendants: false });
        console.log(pathsToCheckout)
        const checkoutGlobber = await glob.create(pathsToCheckout.join('\n'));

        const excludedPaths = await excludeGlobber.glob();
        const pathsToProcess = await checkoutGlobber.glob();

        const filteredPathsToProcess = pathsToProcess.filter(p => !excludedPaths.includes(p));

        for (const dir of filteredPathsToProcess) {
            if (fs.existsSync(path.join(dir, '.git'))) {
                const repoName = await getGitRepoName(dir);
                if (repoName && repos[repoName]) {
                    const ref = repos[repoName];
                    await checkoutRepo(dir, ref);
                }
            }
        }
    } catch (error) {
        core.setFailed(`Action failed with error: ${error}`);
    }
}

main();
