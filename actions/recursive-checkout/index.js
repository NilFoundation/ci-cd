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

async function checkoutRepo(dir, ref, depth = 1) {
    try {
        // Create a temporary branch name based on the ref
        const tempBranch = `temp-${Date.now()}`;

        core.info(`Checkouting ${dir} ${ref} to local ${tempBranch}`);

        // Fetch the specific ref into the temporary branch. This way we could handle
        // SHAs, branches and refs (`refs/pull/%d/merge`) in the same way
        const fetchArgs = ['fetch', 'origin', `${ref}:${tempBranch}`];

        if (depth > 0) {
            fetchArgs.push(`--depth=${depth}`);
        }

        // Fetch the specific ref into the temporary branch
        await exec.exec('git', fetchArgs, {
            cwd: dir
        });

        // Checkout the temporary branch
        await exec.exec('git', ['-C', dir, 'checkout', tempBranch]);
    } catch (error) {
        core.error(`Failed to checkout ${ref} in ${dir}: ${error}`);
        throw error;
    }
}

async function main() {
    try {
        const repoDataLines = core.getMultilineInput('refs');
        const pathsToCheckout = core.getMultilineInput('paths');
        const depth = parseInt(core.getInput('fetch-depth'), 10);

        let repos = {};
        for (const line of repoDataLines) {
            if (line.trim() === '') continue;
            const [repoFullName, ref] = line.split(':').map(part => part.trim());
            repos[repoFullName] = ref;
        }

        // `implicitDescendants` prevents `a` from traversing `a/**`, so you have more control
        const checkoutGlobber = await glob.create(pathsToCheckout.join('\n'), { implicitDescendants: false });

        const pathsToProcess = await checkoutGlobber.glob();

        for (const dir of pathsToProcess) {
            if (fs.statSync(dir).isDirectory()) {
                core.info(`Searching for .git in ${dir}`);
                if (fs.existsSync(path.join(dir, '.git'))) {
                    const repoName = await getGitRepoName(dir);
                    if (repoName && repos[repoName]) {
                        const ref = repos[repoName];
                        await checkoutRepo(dir, ref, depth);
                    }
                }
            }
        }
    } catch (error) {
        core.setFailed(`Action failed with error: ${error}`);
    }
}

main();
