const core = require('@actions/core');
const fs = require('fs');
const junit = require('junit-report-builder');
const os = require('os');
const path = require('path');
const readline = require('readline');

async function generateJUnitReport(inputLines, outputFile) {
    const successPattern = /Built target (.+)/;
    const failurePattern = /make\[\d+\]: Target [`'](.+)[`'] not remade because of errors./;

    let successfulBuilds = [];
    let failedBuilds = [];

    inputLines.forEach(line => {
        const successMatch = line.match(successPattern);
        const failureMatch = line.match(failurePattern);

        if (successMatch) {
            successfulBuilds.push(successMatch[1]);
        } else if (failureMatch) {
            failedBuilds.push(failureMatch[1]);
        }
    });

    var builder = junit.newBuilder()
    var suite = builder.testSuite().name('Build Results');

    successfulBuilds.forEach(success => {
        if (!success.startsWith('_cm_internal_tests-')) {
            suite.testCase()
            .className(success)
            .name('Build Success');
        }
    });

    failedBuilds.forEach(failure => {
        if (failure.endsWith('build')) {
            const targetName = failure.split('/').slice(-2)[0].split('.')[0];
            suite.testCase()
                .className(targetName)
                .name('Build Failure')
                .failure('Build failed for target: ' + targetName);
        }
    });

    builder.writeTo(outputFile);
    console.log(`JUnit report generated: ${outputFile}`);
}

async function main() {
    const inputFile = core.getInput('build-log');
    console.log("file: ", inputFile)
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'junit-builder-'));
    const tempFile = path.join(tempDir, 'build-report.xml');

    let inputLines = [];

    if (inputFile) {
        inputLines = fs.readFileSync(inputFile, 'utf8').split('\n');
    } else {
        // When run ouside of GH Actions, use stdin
        const rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });

        for await (const line of rl) {
            inputLines.push(line);
        }
    }

    await generateJUnitReport(inputLines, tempFile);

    core.setOutput('build-junit-report', tempFile);
}

main();

// Test as: `env 'INPUT_BUILD-LOG=build.log' node index.js `
